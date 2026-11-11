from app.core.config import validate_settings

if __name__ == '__main__':
    try:
        validate_settings()
    except ValueError as error:
        raise SystemExit(str(error)) from None
    print('Configuration valid. No database connection, migration or webhook registration performed.')
