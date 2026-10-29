# mako

a marketing and journaling pipeline. give it a link or a pdf and it researches the company, writes an article and scores the seo :) there is also a chat tab where the model can search the web and scrape pages on its own.

pip install -r requirements.txt, copy .env.example to .env and add your keys, then run python run.py and open localhost:8000 ;)

also: download any draft as .md or .txt via post /api/export-article, and the scorer suggests concrete fixes based on its own metrics (post /api/score-article).
