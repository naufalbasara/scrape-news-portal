# Scraping Tribun News Surabaya
## How to run
 1. Download the source code
	1. Git clone repository
		Do git clone in terminal
		```bash
		git clone https://github.com/naufalbasara/scrape-news-portal.git
		```
	2. Download zip
	<img width="396" alt="image" src="https://github.com/naufalbasara/prife-balance/assets/79196487/f1164607-7e3b-49d3-b585-2729ed6587af">
 2. Activate virtual environment and install requirements
		Mac OS:
	```bash
	python3 -m venv venv # create virtual environment
	source venv/bin/activate # activate environment
	pip install -r requirements.txt # install dependencies
	```
	Windows:
	```bash
	python -m venv venv # create virtual environment
	venv\Scripts\activate # activate environment
	pip install -r requirements.txt # install dependencies
	```
 3. Run program (main.py) 
	 `python src/main.py`

  4. Change running behavior
Tweak the input in the variables below (selected_menu, time_filter, months_back)
<img width="654" alt="image" src="https://github.com/naufalbasara/scrape-news-portal/assets/79196487/aec67652-9dc7-41c8-bb57-3adae1dfd58a">