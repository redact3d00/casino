import csv
import json
from io import StringIO
from datetime import datetime, timedelta
import secrets
import string

def format_currency(amount):
    """Форматирование суммы в валюту"""
    return f"${amount:,.2f}"

def generate_reference(prefix='REF'):
    """Генерация уникальной ссылки"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"{prefix}_{timestamp}_{random_str}"

def export_to_csv(data, filename='report.csv'):
    """Экспорт данных в CSV"""
    if not data:
        return ''
    
    output = StringIO()
    
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        # Если это список словарей
        fieldnames = data[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    else:
        # Если это список списков
        writer = csv.writer(output)
        writer.writerows(data)
    
    output.seek(0)
    return output.getvalue()

def calculate_age(birth_date):
    """Расчет возраста"""
    today = datetime.now().date()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def format_date(date_obj, format_str='%Y-%m-%d %H:%M:%S'):
    """Форматирование даты"""
    if not date_obj:
        return ''
    return date_obj.strftime(format_str)

def truncate_string(text, length=100):
    """Обрезка строки"""
    if not text:
        return ''
    if len(text) <= length:
        return text
    return text[:length] + '...'

def get_time_ago(timestamp):
    """Время назад в читаемом формате"""
    now = datetime.now()
    diff = now - timestamp
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"