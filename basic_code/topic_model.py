#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 18 15:06:52 2021

@author: Danielle Lambion
"""
# These imports can be removed when porting to the cloud
import time
import tracemalloc

# We need to keep these ones
import pandas as pd
import gensim
#from gensim import corpora, models
from gensim import models
#from gensim.utils import simple_preprocess
#from gensim.parsing.preprocessing import STOPWORDS
from nltk.stem import WordNetLemmatizer, SnowballStemmer
#from nltk.stem.porter import *
#import numpy as np
#np.random.seed(2018)
import nltk
nltk.download('wordnet')

# =============================================================================
# Create a token word dictionary. Tokens that appear in less than 15 headlines
# are removed. Tokens appearing in more than 50% of the corpus are removed.
# =============================================================================
def create_dict(docs):
    dictionary = gensim.corpora.Dictionary(docs)
    dictionary.filter_extremes(no_below=15, no_above=0.5)
    return dictionary

# =============================================================================
# Create a TFIDF model from a bag-of-words generated by the corpus dictionary.
# =============================================================================
def create_tfidf_model(docs, dictionary):
    bow_corpus = [dictionary.doc2bow(doc) for doc in docs]
    tfidf = models.TfidfModel(bow_corpus)
    corpus_tfidf = tfidf[bow_corpus]
    return corpus_tfidf

# =============================================================================
# Tokenize the String text. Stopwords and words less than 3 characters are
# removed. Words are stemmed and lemmatized and tokens are returned in
# their root form.
# =============================================================================
def process_data(text):
    processed_text = []
    for token in gensim.utils.simple_preprocess(text):
        if token not in gensim.parsing.preprocessing.STOPWORDS and len(token) > 2:
            # lemmatizing verbs
            lemtext = WordNetLemmatizer().lemmatize(token, pos='v')
            # reduce to root form
            stemttext = SnowballStemmer("english").stem(lemtext)
            processed_text.append(stemttext)
    return processed_text


# =============================================================================
# Queries the model for the topic number, match score, and topic and appends
# this information onto the query dataframe.
# =============================================================================
def get_topic(df, model, tfidf):
    topics_df = pd.DataFrame()
    for tfidf_val in tfidf:
        for index, score in sorted(model[tfidf_val], key=lambda tup: -1*tup[1]):
            #print("\nScore: {}\t \nTopic: {}".format(score, model.print_topic(index, 10)))
            topics_df = topics_df.append(pd.Series([index,score,model.print_topic(index, 10)]),
                                         ignore_index=True)
    topics_df.columns = ['topic_number', 'score', 'topic']
    return df.join(topics_df)

# =============================================================================
# Method simulates our data processing pipeline.
# Timing and memory usage code can be removed for cloud application.
# =============================================================================
def main():
# =============================================================================
#     This would be Lambda function 1 on AWS
# =============================================================================
    function1_time = time.time()
    tracemalloc.start()
# =============================================================================
#     LOAD news_train.csv FROM S3 BUCKET
#     We will use the last 80% of the dataset for model training
# =============================================================================
    df = pd.read_csv("../data/news_train.csv",error_bad_lines=False,
                     usecols=['publish_date', 'headline_text'])    
    df['processed_text'] = df['headline_text'].apply(lambda x: process_data(x))
    dictionary = create_dict(df['processed_text'])
    corpus_tfidf = create_tfidf_model(df['processed_text'], dictionary)
# =============================================================================
#     SAVE corpus_tfidf AND dictionary TO S3 BUCKET
# =============================================================================
    current, peak = tracemalloc.get_traced_memory()
    function1_time = time.time() - function1_time
    print(f"Function 1 memory usage peak was {peak / 10**6} MB")
    tracemalloc.stop()
    print("Function 1 Runtime:", function1_time, "seconds")
   
    
# =============================================================================
#     This would be Lambda function 2 on AWS
# =============================================================================
    function2_time = time.time()
    tracemalloc.start()
# =============================================================================
#     LOAD corpus_tfidf AND dictionary FROM S3 BUCKET
# =============================================================================
    lda_model = gensim.models.LdaMulticore(corpus_tfidf, num_topics=5,
                                           id2word=dictionary, passes=2,
                                           workers=2)
# =============================================================================
#     SAVE lda_model TO S3 BUCKET
# =============================================================================
    #lda_model.save('lda.moddel')
    current, peak = tracemalloc.get_traced_memory()
    function2_time = time.time() - function2_time
    print(f"Function 2 memory usage peak was {peak / 10**6} MB")
    tracemalloc.stop()
    print("Function 2 Runtime:", function2_time, "seconds")
    
# =============================================================================
#     i = 0
#     while(i<3):
#         i+=1
#         for index, score in sorted(lda_model[corpus_tfidf[i]], key=lambda tup: -1*tup[1]):
#             print(lda_model[corpus_tfidf[i]])
#             print("\nScore: {}\t \nTopic: {}".format(score, lda_model.print_topic(index, 10)))
#     print("first finished")
# =============================================================================
    
# =============================================================================
#     This would be Lambda function 3 on AWS
#
#     Querying the model may not stress the system
#     We may need to make multiple, synchronous calls
# =============================================================================
    function3_time = time.time()
    tracemalloc.start()
# =============================================================================
#     LOAD lda_model AND dictionary AND news_test.csv FROM S3 BUCKET
#     We will use the last 20% of the dataset to query the model
# =============================================================================
    df_query = pd.read_csv("../data/news_test.csv",error_bad_lines=False,
                           usecols=['publish_date', 'headline_text'])
    df_query['processed_text'] = df_query['headline_text'].apply(lambda x: process_data(x))
    #dictionary_query = create_dict(df_query['processed_text'])
    query_tfidf = create_tfidf_model(df_query['processed_text'], dictionary)
    #query_bow = [dictionary.doc2bow(doc) for doc in df_query['processed_text']]
    df_query = get_topic(df_query, lda_model, query_tfidf)
    print(df_query['processed_text'])
    print(df_query['headline_text'])
    print(df_query['topic_number'])
    print(df_query['score'])
    print(df_query['topic'])
# =============================================================================
#     SAVE df_query AS A CSV TO S3 BUCKET
#    (or return it to wherever user might want it)
# =============================================================================
    df_query.to_csv("../data/results.csv")
    current, peak = tracemalloc.get_traced_memory()
    function3_time = time.time() - function3_time
    print(f"Function 3 memory usage peak was {peak / 10**6} MB")
    tracemalloc.stop()
    print("Function 3 Runtime:", function3_time, "seconds")


if __name__ == "__main__":
    main()