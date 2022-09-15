# Finance_reddit_scraping
## Structure
The script checks the volume of four large reddit finance forums, WBS, Stocks, Investing and Pennystocks.

After finding the volume the script either scrapes the top two WBS posts if the forum has had over 2000 posts that day (or if the average posts over the last four days has been over 1500). It subsequently finds the most popular tickers mentioned on WBS and sends it to an email. 

Note: you need an email client that can send the emails. I'm using sendinblue which allows 300 free emails each day. See the website and documentation for guidance if you want to send emails.

If the volume is below the set conditions the script will instead scrape forums Stocks, Investing and Pennystocks and finding the most mentioned tickers on these forums. Then sends the result through the email client to the selected contacts.

