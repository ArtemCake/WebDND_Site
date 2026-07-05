# web/core/dependencies.py

from Config.imports import (OAuth2PasswordBearer, Request, Depends,
                                 HTTPException, status, JWTError, select, selectinload, Form, DefaultForm)
from app.core.security import decode_token
from app.database.session import get_async_db
from app.database.models import User # Импортируем модели


# Определяем схему здесь, в глобальной области модуля
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def OverloadedForm(value: str = Form(...)):
	return DefaultForm(value)

# --- ИЗМЕНЯЕМ ЗАВИСИМОСТЬ ---
async def get_current_user(request: Request):
	credentials_exception = HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail="Could not validate credentials",
		headers={"WWW-Authenticate": "Bearer"},
	)
	user_db = None
	db_manager = get_async_db()
	async with (db_manager as db):
		try:
			token = request.headers.get("Authorization")
			if not token:
				cookie_token = request.cookies.get("access_token")
				if cookie_token:
					token = cookie_token.replace("Bearer ", "")
			if not token:
				raise credentials_exception
			payload = decode_token(token)
			username: str = payload.get("sub")
			if username is None:
				raise credentials_exception
		except JWTError:
			raise credentials_exception
		user_id = int(username)
		stmt = select(User).options(
			selectinload(User.characters),
		).where(User.id == user_id)
		user_result = await db.execute(stmt)
		user = user_result.scalars().first()
		if user is None:
			raise credentials_exception
		user_db = user
	return user_db
