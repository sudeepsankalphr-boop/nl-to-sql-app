from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import get_db
from models import User, UploadedFile, QueryHistory
import jwt
import os
from anthropic import Anthropic
import json
import re

router = APIRouter(prefix="/query", tags=["query"])

JWT_SECRET = os.getenv("JWT_SECRET", "test-secret-key")
ALGORITHM = "HS256"

client = Anthropic()

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="No token")
    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_csv_schema(csv_data: str) -> str:
    lines = csv_data.strip().split('\n')
    if not lines:
        return ""
    header = lines[0]
    return header

def build_prompt(schema: str, question: str, sample_rows: str) -> str:
    return f"""You are a SQL expert. Generate a SQLite SELECT query for this question.

CSV Schema (columns):
{schema}

Sample data (first 3 rows):
{sample_rows}

Question: {question}

Rules:
1. Generate ONLY the SELECT statement
2. No explanations, no markdown
3. Use standard SQLite syntax
4. Make sure column names match exactly

Return ONLY the SQL query, nothing else."""

def validate_sql(sql: str) -> bool:
    dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE']
    for keyword in dangerous:
        if keyword in sql.upper():
            return False
    if 'SELECT' not in sql.upper():
        return False
    return True

def execute_query(csv_data: str, sql: str) -> dict:
    import sqlite3
    import io
    
    lines = csv_data.strip().split('\n')
    if len(lines) < 2:
        raise Exception("CSV too small")
    
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    # Create temp table from CSV
    import csv
    reader = csv.DictReader(io.StringIO(csv_data))
    rows = list(reader)
    
    if not rows:
        raise Exception("No data")
    
    cols = list(rows[0].keys())
    col_names = ', '.join([f'"{c}"' for c in cols])
    
    create_sql = f"CREATE TABLE data ({col_names})"
    cursor.execute(create_sql)
    
    placeholders = ', '.join(['?' for _ in cols])
    insert_sql = f"INSERT INTO data VALUES ({placeholders})"
    
    for row in rows:
        values = [row.get(c, '') for c in cols]
        cursor.execute(insert_sql, values)
    
    conn.commit()
    
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        col_names = [desc[0] for desc in cursor.description]
        conn.close()
        
        return {
            "columns": col_names,
            "rows": [dict(zip(col_names, row)) for row in results],
            "count": len(results)
        }
    except Exception as e:
        conn.close()
        raise Exception(f"Query execution failed: {str(e)}")

@router.post("/ask")
def ask_question(
    file_id: str,
    question: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Get file
    file = db.query(UploadedFile).filter(
        UploadedFile.id == file_id,
        UploadedFile.user_id == user.id
    ).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Get schema
    schema = get_csv_schema(file.csv_data)
    
    # Get sample rows
    sample_lines = file.csv_data.split('\n')[:4]
    sample_rows = '\n'.join(sample_lines)
    
    # Build prompt
    prompt = build_prompt(schema, question, sample_rows)
    
    # Call Claude
    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        generated_sql = message.content[0].text.strip()
        
        # Validate
        if not validate_sql(generated_sql):
            raise HTTPException(status_code=400, detail="Generated SQL contains unsafe operations")
        
        # Execute
        result = execute_query(file.csv_data, generated_sql)
        
        # Save to history
        history = QueryHistory(
            user_id=user.id,
            file_id=file_id,
            question=question,
            generated_sql=generated_sql,
            results=json.dumps(result)
        )
        db.add(history)
        db.commit()
        
        return {
            "question": question,
            "sql": generated_sql,
            "data": result,
            "row_count": result["count"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")