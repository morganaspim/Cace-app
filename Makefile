.PHONY: test run qualify-v330

test:
	python -m pytest

run:
	python -m cace_studio.app

qualify-v330:
	bash scripts/qualify_v330_portable.sh
