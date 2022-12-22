download:
	scrapy crawl haokan2
	rm STATUS.txt
	make download

exception:
	python3 __exception__.py
	make download
