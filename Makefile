setup:
	pip3 install --upgrade numpy
	pip3 install -r requirements.txt
	python3 setup.py install

test_local:
	-mkdir /tmp/sdaas
	pytest -v  tests

test:
	-mkdir /tmp/sdaas
	pytest -v  tests --runslow

style:
	find dj_feet tests -name \[a-zA-Z_]*.py -exec pep8 --ignore=E402 {} +

coverage_local:
	pytest -v --cov-config=.coveragerc --cov=dj_feet tests/

coverage:
	pytest -v --cov-config=.coveragerc --cov=dj_feet --runslow tests/
