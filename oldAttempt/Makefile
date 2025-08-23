.PHONY: build serve validate clean

build:
	python3 generate_docs.py --input-dir docs --template docs.html --output docs.html

serve:
	python3 -m http.server 8000

validate:
	python3 scripts/validate.py

clean:
	@echo "Nothing to clean"
