#!/usr/bin/env python3
"""
Скрипт для исправления моделей SQLAlchemy в соответствии с новыми версиями.
"""
import os
import re
import sys

def fix_relationships_in_file(filepath):
    """Исправляет relationship.backref в файле модели."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Исправляем проблемы с relationship.backref
    if 'relationship.backref' in content:
        print(f"Fixing relationship.backref in: {filepath}")
        
        # Находим все вхождения и заменяем их
        pattern = r'relationship\([^)]*backref=relationship\.backref\(([^)]*)\)[^)]*\)'
        
        def replace_backref(match):
            backref_content = match.group(1)
            
            # Извлекаем имя backref и remote_side если есть
            backref_match = re.search(r'"([^"]+)"', backref_content)
            remote_match = re.search(r'remote_side=\[([^]]+)\]', backref_content)
            
            if backref_match:
                backref_name = backref_match.group(1)
                
                # Заменяем весь match
                new_rel = match.group(0).replace(f'backref=relationship.backref({backref_content})', f'backref="{backref_name}"')
                
                # Если есть remote_side, добавляем его отдельно
                if remote_match:
                    remote_side = remote_match.group(1)
                    
                    # Удаляем remote_side из backref и добавляем его как отдельный параметр
                    new_rel = new_rel.replace(f'backref="{backref_name}"', f'backref="{backref_name}", remote_side=[{remote_side}]')
                
                return new_rel
            
            return match.group(0)
        
        modified_content = re.sub(pattern, replace_backref, content)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(modified_content)
            
        print(f"Fixed relationship.backref in: {filepath}")
        return True
    
    return False


def fix_models(directory):
    """Исправляет все модели в указанной директории."""
    fixed_files = 0
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if fix_relationships_in_file(filepath):
                    fixed_files += 1
    
    return fixed_files

def create_fix_script():
    """Создает PowerShell скрипт для Windows для выполнения исправлений."""
    script_content = """
# Скрипт для исправления моделей и установки зависимостей

# Установка необходимых пакетов
Write-Host "Installing required packages..."
pip install pydantic-settings motor redis

# Инструкции для пользователя
Write-Host "===================================="
Write-Host "Зависимости установлены. Теперь запустите приложение:"
Write-Host "uvicorn app.main:app --reload"
Write-Host "===================================="
"""
    
    with open("fix_dependencies.ps1", 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print("Created fix_dependencies.ps1 script - run it to install required dependencies.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "app/models"  # По умолчанию директория моделей
    
    fixed_count = fix_models(directory)
    print(f"Fixed {fixed_count} files in {directory}")
    
    # Создаем скрипт для установки зависимостей
    create_fix_script()
    
    print("""
INSTRUCTIONS:
1. Run the fix_dependencies.ps1 script to install required packages:
   ./fix_dependencies.ps1

2. Then start your application:
   uvicorn app.main:app --reload
    """)