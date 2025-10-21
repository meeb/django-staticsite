python=/usr/bin/env python


test:
		uv run manage.py testsuite


runserver:
		uv run run-tests.py runserver
