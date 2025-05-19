#!/usr/bin/env python3
"""
Скрипт для исправления всех моделей SQLAlchemy в проекте.
"""
import os
import re
import sys


def fix_relationship_backref(content):
    """Исправляет проблемы с relationship.backref в коде."""
    if 'relationship.backref' not in content:
        return content, False
    
    pattern = r'backref=relationship\.backref\("([^"]+)",[^)]*?remote_side=\[[^]]+\][^)]*?\)'
    replacement = r'backref="\1", remote_side=[id]'
    
    # Если есть проблемные записи
    new_content = re.sub(pattern, replacement, content)
    return new_content, new_content != content


def fix_file(file_path):
    """Исправляет проблемы с SQLAlchemy в файле."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Исправляем relationship.backref
        new_content, changed_backref = fix_relationship_backref(content)
        
        if changed_backref:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Fixed relationship.backref in: {file_path}")
            return True
        
        return False
    except Exception as e:
        print(f"Error fixing file {file_path}: {e}")
        return False


def fix_all_models(directory):
    """Исправляет все модели в указанной директории и поддиректориях."""
    fixed_files = 0
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_file(file_path):
                    fixed_files += 1
    
    return fixed_files


if __name__ == "__main__":
    # Директория по умолчанию - текущая директория приложения
    directory = os.path.dirname(os.path.abspath(__file__))
    
    # Или указанная пользователем директория
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    
    print(f"Scanning directory: {directory} for SQLAlchemy models to fix...")
    
    fixed_count = fix_all_models(directory)
    print(f"Fixed {fixed_count} files.")
    
    # Инструкции по установке зависимостей
    print("""
INSTRUCTIONS:
1. Install required packages:
   pip install pydantic-settings redis motor

2. Start the application:
   uvicorn app.main:app --reload
    """)