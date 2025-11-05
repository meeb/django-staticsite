python=/usr/bin/env python


test:
		uv run manage.py testsuite


lint:
		uvx ruff check


runserver:
		uv run manage.py runserver
