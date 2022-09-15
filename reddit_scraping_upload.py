# -*- coding: utf-8 -*-
"""
Created on Thu Sep 15 10:20:27 2022

@author: pj20
"""

#### Import packages
import pandas as pd
import numpy as np
import re
import itertools
import praw
import datetime
import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from pprint import pprint
from datetime import timedelta
import time
import requests

# Inputs 
directory = "input working directory"

# Reddit API credentials
client_id= 'input client id'
client_secret = "input client secret"
user_agent="input user agent"

# sendinblue API credentials
api_kei_sendinBlue = "input email api key"
email = "input email"

# set wotking directory
os.chdir(directory)


# Scraping volume of the four largest Reddit finance forums
now = datetime.datetime.now()
subreddits = ['stocks','investing','pennystocks','wallstreetbets']


stocks = []
investing = []
penny = []
WBS = []
indx = []

nSubmissions = []
for day in range(1,10):
    for sub in subreddits:
        r = requests.get(f"https://api.pushshift.io/reddit/search/submission/?subreddit={sub}&metadata=true&size=0&after={day}d&before={day-1}d")
        time.sleep(1.5)
        res = r.json()['metadata']['total_results']
        if sub == subreddits[0]:
            stocks.append(res)
        elif sub == subreddits[1]:
            investing.append(res)
        elif sub == subreddits[2]:
            WBS.append(res)
        elif sub == subreddits[3]:
            penny.append(res)
            indx.append(pd.to_datetime(now-timedelta(days=day)))


d = {subreddits[0]:stocks, subreddits[1]:investing, subreddits[2]:WBS, subreddits[3]:penny}
nSubmissions = pd.DataFrame(index =indx,data=d)

# nSubmissions.to_csv('Number of submissions.csv')
nSubmissions['wallstreetbets'].plot()

rol = nSubmissions['wallstreetbets'].sort_index(ascending = False).rolling(4).mean()


# If the volume of WBS is larger than 2000 posts, or the average post activity is large, scrape WBS and send the
# result and the total volume through email.
# Else send a summary of the tickers that are being discussed on other forums and the total volume for all four forums.



if np.logical_or(nSubmissions['wallstreetbets'][0]>2000,
                 any([i>1500 for i in rol[(len(rol)-4):len(rol)]])):
    
    subreddits = ['wallstreetbets']
    submissions = [2]

    #### SCRAPING REDDIT
    now = datetime.datetime.now()
    reddit = praw.Reddit(client_id= client_id,
                         client_secret = client_secret,
                         user_agent=user_agent,check_for_async=False)
    
    
    resultAll = []
    for sub,number in zip(subreddits,submissions):
        
        file = open(str(now.year)+str(now.month)+str(now.day)+" "+sub+".txt","w",encoding="utf_8") #!!!
        
        file.write('Type;iD;Parent_iD;Author;Title;Post;Timestamp;Child_Elements'+"\n")
        
        for submission in reddit.subreddit(sub).hot(limit=number): #!!!
            subm = "Submission;"+\
                str(submission.id).replace(";",",")+";"+\
                str(submission.subreddit_id).replace(";",",")+";"+\
                str(submission.author).replace(";",",")+";"+\
                str.strip(submission.title).replace(";",",")+";"+\
                str.strip(submission.selftext).replace(";",",")+";"+\
                str(submission.created_utc).replace(";",",")+";"+\
                str(submission.num_comments)
            file.write(subm.replace("\n"," ").replace("\r"," ").replace("\t"," ")+"\n")
            
            submission.comments.replace_more(limit=None)
            for comment in submission.comments.list():
                comm = "Comment;"+\
                str(comment.id).replace(";",",")+";"+\
                str(comment.parent_id).replace(";",",")+";"+\
                str(comment.author).replace(";",",")+";"+\
                ";"+\
                str.strip(comment.body).replace(";",",")+";"+\
                str(comment.created_utc).replace(";",",")
        
                file.write(comm.replace("\n"," ").replace("\r"," ").replace("\t"," ")+"\n")
        
        file.close()
        
        
        #### Count the number of tickers
        df = pd.read_csv(str(now.year)+str(now.month)+str(now.day)+" "+sub+".txt", sep =';') #!!!
        
        
        df['tickers']  = " "
        
        tickers  = []
        for i,post in enumerate(df['Post']):  #!!!
            try:
                if len(re.findall(r'(?<=\$)\w+|[A-Z]{3,6}', post)) > 0:
                    tickers.append(re.findall(r'(?<=\$)\w+|[A-Z]{3,6}', post))
                    df['tickers'][i] = re.findall(r'(?<=\$)\w+|[A-Z]{3,6}', post)
            except TypeError:
                print(1)
        
        tickers = [item[0].split(",") for item in tickers]
        tickers = list(itertools.chain.from_iterable(tickers))
        
        my_dict = {i:tickers.count(i) for i in tickers}
        result = pd.Series(my_dict).to_frame().reset_index().rename(columns = {'index':'ticker', 0:'count'}) #!!!
        resultAll.append(result.sort_values(by=['count'],axis=0,ascending=False,ignore_index=True).head(10)) #!!!


    resultWbs = resultAll[0]
    
    
    
    #### Send data through email
    html1 = """\
    <html>
      <head></head>
      <body>
        {0}
      </body>
    </html>
    """.format(resultWbs.to_html())
    

    ####
    
    html2 = """\
    <html>
      <head></head>
      <body>
        {0}
      </body>
    </html>
    """.format(nSubmissions.to_html())
    
    ###
    
    report = ""
    report += html1
    report += "<br><br>"
    report += html2


    
    now = datetime.datetime.now()
    n = 1
    # Add 2 minutes to datetime object containing current time
    future_time = now + timedelta(minutes=n)
    # Convert datetime object to string in specific format 
    future_time_str = future_time.strftime('%Y-%m-%d %H:%M:%S.%f')
    
    
    # Instantiate the client\
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = api_kei_sendinBlue
    api_instance = sib_api_v3_sdk.EmailCampaignsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    # Define the campaign settings\
    email_campaigns = sib_api_v3_sdk.CreateEmailCampaign(
    name= "Result from scraping",
    subject= "WBS high volume on the "+str(now)[:10],
    sender= { "name": "Mattias Haughom", "email": email},
    # Content that will be sent\
    html_content= report,
    # Schedule at
    scheduled_at = future_time_str,
    # Select the recipients\
    recipients= {"listIds": [4]}
    )
    # Make the call to the client\
    try:
        api_response = api_instance.create_email_campaign(email_campaigns)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling EmailCampaignsApi->create_email_campaign: %s\n" % e)

else:
    
    subreddits = ['stocks','investing','pennystocks']
    submissions = [20,40,100]
    
    #### SCRAPING REDDIT
    now = datetime.datetime.now()
    reddit = praw.Reddit(client_id= client_id,
                         client_secret = client_secret,
                         user_agent=user_agent,check_for_async=False)
    
    
    resultAll = []
    for sub,number in zip(subreddits,submissions):
        
        file = open(str(now.year)+str(now.month)+str(now.day)+" "+sub+".txt","w",encoding="utf_8") #!!!
        
        file.write('Type;iD;Parent_iD;Author;Title;Post;Timestamp;Child_Elements'+"\n")
        
        for submission in reddit.subreddit(sub).hot(limit=number): #!!!
            subm = "Submission;"+\
                str(submission.id).replace(";",",")+";"+\
                str(submission.subreddit_id).replace(";",",")+";"+\
                str(submission.author).replace(";",",")+";"+\
                str.strip(submission.title).replace(";",",")+";"+\
                str.strip(submission.selftext).replace(";",",")+";"+\
                str(submission.created_utc).replace(";",",")+";"+\
                str(submission.num_comments)
            file.write(subm.replace("\n"," ").replace("\r"," ").replace("\t"," ")+"\n")
            
            submission.comments.replace_more(limit=None)
            for comment in submission.comments.list():
                comm = "Comment;"+\
                str(comment.id).replace(";",",")+";"+\
                str(comment.parent_id).replace(";",",")+";"+\
                str(comment.author).replace(";",",")+";"+\
                ";"+\
                str.strip(comment.body).replace(";",",")+";"+\
                str(comment.created_utc).replace(";",",")
        
                file.write(comm.replace("\n"," ").replace("\r"," ").replace("\t"," ")+"\n")
        
        file.close()
        
        
        
        #### Count the number of tickers
        df = pd.read_csv(str(now.year)+str(now.month)+str(now.day)+" "+sub+".txt", sep =';') #!!!
        
        
        df['tickers']  = " "
        
        tickers  = []
        for i,post in enumerate(df['Post']):  #!!!
            try:
                if len(re.findall(r'(?<=\$)\w+|[A-Z]{3,6}', post)) > 0:
                    tickers.append(re.findall(r'(?<=\$)\w+|[A-Z]{3,6}', post))
                    df['tickers'][i] = re.findall(r'(?<=\$)\w+|[A-Z]{3,6}', post)
            except TypeError:
                print(1)
        
        tickers = [item[0].split(",") for item in tickers]
        tickers = list(itertools.chain.from_iterable(tickers))
        
        my_dict = {i:tickers.count(i) for i in tickers}
        result = pd.Series(my_dict).to_frame().reset_index().rename(columns = {'index':'ticker', 0:'count'}) #!!!
        resultAll.append(result.sort_values(by=['count'],axis=0,ascending=False,ignore_index=True).head(5)) #!!!
    
    resultStocks = resultAll[0]
    resultInvesting = resultAll[1]
    resultPennystocks = resultAll[2]

    
    
    #### Send data through email
    
    
    html1 = """\
    <html>
      <head></head>
      <body>
        {0}
      </body>
    </html>
    """.format(resultStocks.to_html())
    
    
    html2 = """\
    <html>
      <head></head>
      <body>
        {0}
      </body>
    </html>
    """.format(resultInvesting.to_html())
    
    
    html3 = """\
    <html>
      <head></head>
      <body>
        {0}
      </body>
    </html>
    """.format(resultPennystocks.to_html())
    
    
    html4 = """\
    <html>
      <head></head>
      <body>
        {0}
      </body>
    </html>
    """.format(nSubmissions.to_html())
    
    
    ###
    
    report = "Here are some other tickers that are being discussed on other forums:"
    report += "<br><br>"
    report += "r\Stocks"
    report += html1
    report += "<br><br>"
    report += "r\Investing"
    report += html2
    report += "<br><br>"
    report += "r\PennyStocks"
    report += html3
    report += "<br><br>"
    report += html4
    
    
    now = datetime.datetime.now()
    n = 1
    # Add 2 minutes to datetime object containing current time
    future_time = now + timedelta(minutes=n)
    # Convert datetime object to string in specific format 
    future_time_str = future_time.strftime('%Y-%m-%d %H:%M:%S.%f')
    
    
    # Instantiate the client\
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = api_kei_sendinBlue
    api_instance = sib_api_v3_sdk.EmailCampaignsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    # Define the campaign settings\
    email_campaigns = sib_api_v3_sdk.CreateEmailCampaign(
    name= "Result from scraping",
    subject= "WBS volume is low today",
    sender= { "name": "Mattias Haughom", "email": email},
    # Content that will be sent\
    html_content= report,
    # Schedule at
    scheduled_at = future_time_str,
    # Select the recipients\
    recipients= {"listIds": [4]}
    )
    # Make the call to the client\
    try:
        api_response = api_instance.create_email_campaign(email_campaigns)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling EmailCampaignsApi->create_email_campaign: %s\n" % e)


















