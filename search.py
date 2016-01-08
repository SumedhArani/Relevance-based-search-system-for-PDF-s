import sys
import glob
import time
import re
import collections
import pickle
import nltk
from nltk.corpus import stopwords
import PyPDF2
import vecsea
from pgreader import getPdf
#------------------------------------------------------------------------------------
common_text =stopwords.words('english1') #Self created list of stopwords
#------------------------------------------------------------------------------------
def run(ques_file):
    porter =nltk.PorterStemmer() #used for stemming of a word

    fsea =open('{0}.pickle'.format(sys.argv[1].split('.')[0]),'rb')
    index_dict =pickle.load(fsea) #de-serialization of index(dict)
    fsea.close()
    
    fvec =open('{0}_vec.pickle'.format(sys.argv[1].split('.')[0]),'rb')
    vector_doc =pickle.load(fvec) #de-serialization of vectors(list of lists)
    fvec.close()
    #--------------------------------------------------------------------------------
    def words(text_list):
        a=[]
        for text_dict in text_list[1:]:
            for text in text_dict:
                a.append(re.findall('[a-z]+', text.lower()))
        return a

    def train(feature_list):
        model = collections.defaultdict(lambda: 1)
        for features in feature_list:
            for f in features:
                model[f] += 1
        return model

    NWORDS = train(words(vector_doc))

    alphabet = 'abcdefghijklmnopqrstuvwxyz'

    def edits1(word):
        splits     = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        deletes    = [a + b[1:] for a, b in splits if b]
        transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b)>1]
        replaces   = [a + c + b[1:] for a, b in splits for c in alphabet if b]
        inserts    = [a + c + b     for a, b in splits for c in alphabet]
        return set(deletes + transposes + replaces + inserts)

    def known_edits2(word):
        return set(e2 for e1 in edits1(word) for e2 in edits1(e1) if e2 in NWORDS)
    
    def known(words):
        return set(w for w in words if w in NWORDS)

    def correct(word):
        candidates = known([word]) or known(edits1(word)) or known_edits2(word) or [word]
        return max(candidates, key=NWORDS.get)
    #--------------------------------------------------------------------------------
    pdf_obj = PyPDF2.PdfFileReader(sys.argv[1]) #object instantiation
    def getPage(page_no):
        page = pdf_obj.getPage(page_no)
        page_content = ''
        for page_list in page.extractText().split("\n"):
            page_content = page_content + page_list.strip()+' '#use of strip to get rid of unnecessary spaces(if present)
        return page_content
    #---------------------------------------------------------------------------------------
    def find_set(search_str):
        #finds all sets containing the search string
        count =2 #index_dict KEY:"first three letters" hence, 012->count=2
        prev_count=2 
        match =[]
        try:
            search_list =index_dict[search_str[:3]] #searches our indexed data
        except:
            return(-1,prev_count) 
        new =[x[1] for x in search_list]
        while(prev_count==count):
            count+=1
            if len(new)!=0:
                prev_count =count
                match =new
                try:
                    search_list =list(filter(lambda y:len(y[0])>count and y[0][count]==search_str[count],search_list))
                    new =[x[1] for x in search_list] #keep eliminating the search list letter by letter
                except:
                    new=[]
        return(set(match),prev_count) #returns the set having the page num & count till where it finds longest match
    #-------------------------------------------------------------------------------
    #Reading the question/s
    try:
        fqs =open(ques_file[0],'r+')
        qset =fqs.read().split('\n')
        fqs.close()
    except:
        question =' '.join(sys.argv[2:])
        qset =[question] #list of ques, here it is only one
    #--------------------------------------------------------------------------------
    qcount =0 #count of question number
    for each_ques in qset:
        ans_set =[]
        qcount+=1 #inc count of ques no. every time the loop goes through
        if len(each_ques)>1:
            text =nltk.wordpunct_tokenize(each_ques) #tokenise the words in the question
            normalized_text =[p.lower() for p in text if p.isalpha() and len(p)>2] #min search criteria, enter 3 letter
            key_terms =list(set(normalized_text)-set(common_text)) #remove stopwords
            key_terms =[correct(t) for t in key_terms] #correct the spelling
            key_terms =[porter.stem(t) for t in key_terms] #stem each word
            key_term_match =[]
            #---------------------------------------------------------------------------
            for key_term in key_terms: #iterate the keywords in the ques and find the set of pg num containg the word
                res,lpfix =find_set(key_term) #set result & longest prefix match
                key_term_match.append((key_term,lpfix))
                if res != -1:
                    ans_set.append(res) #append sets to a common list
            #---------------------------------------------------------------------------
            if len(ans_set) !=0:
                search_res =eval('&'.join([str(f) for f in ans_set])) #anding all sets
            #--------------------------------------------------------------------------
                relevant_res =[]
                for pg in search_res:
                    proportion =[]
                    sarea =vector_doc[pg] #fetch the page's term data using the indexed data
                    #-----------------------------
                    for key_term in key_term_match:
                        try:
                            for z in sarea:
                                if key_term[0][:key_term[1]] in z: 
                                    proportion.append(sarea[z]/sarea['#SUM']) #normalize and find proportion
                                else:
                                    proportion.append(0)
                        except:
                            proportion.append(0)
                    #-------------------------------------------------------------------------
                    proportion_val =sum(proportion) #find the sum of all the proportions
                    relevant_res.append((proportion_val,pg))
                    pg_key ={}
                    for m in relevant_res:
                        if m[1] not in pg_key:
                            pg_key[m[1]]=m[0]
                        else:
                            pg_key[m[1]]+=m[0]
                    page_res =[]
                    for q in pg_key:
                        page_res.append((q,pg_key[q]))
                    page_res.sort(key=lambda a:a[1],reverse=True)
                    search_range =page_res[0][1]-(page_res[0][1]*0.30) #30% of the bell curve
                    result =[x[1] for x in page_res]
                    p_res =[x[0] for x in page_res]
            else:
                print("No answers found")
                break
            #------------------------------------------------------------------------------------
            #Clustered weighting
            pu =[[],[]] #[Best hits, other hits] #pu  -penultimate res
            for n in range(len(relevant_res)):
                if page_res[n][1]>search_range:
                    pu[0].append(page_res[n][0])
                else:
                    pu[1].append(page_res[n][0])
            #-------------------------------------------
            final =[]      
            cl_count =-1
            for rq in pu[0]:
                cl_count+=1
                final.append([rq])
                for rs in pu[0]:
                    if rq-4<rs<rq+4:
                        if rs not in final[cl_count]:
                            final[cl_count].append(rs)
                for rt in pu[1]:
                    if rq-4<rt<rq+4:
                        if rt not in final[cl_count]:
                            final[cl_count].append(rt)
            final.sort(key =len,reverse =True)
            f_avg =list(map(lambda a:sum(a)/len(a),final))
            f_res =len(list(filter(lambda x:f_avg[0]>=x>(f_avg[0]-5),f_avg)))
            final_ans =eval('|'.join([str(set(f)) for f in final[:f_res]])) #Final result
            final_ans =list(final_ans)
            final_ans.sort()
            print("Best search hits are:\n1. ",end=" ")
            s =""
            for a in range(1,len(final_ans)):
                s =s+' '+str(final_ans[a-1])
                if final_ans[a]-final_ans[a-1]>5:
                    print("\n2. ",end=" ")
            s=s+' '+str(final_ans[-1])
            print(s)
            
            #--------------------------------------------
            '''
             #Printing the answer
            print("Answer to Q -",qcount)
            print('*-'*50)
            for page_no in final_ans:
                print('Page no: ',page_no,'\t','-----'*20)
                print(getPage(page_no-1))
                print('-----'*20,'\n')
            print('*-'*50)
            print('\n\n')
            '''
#------------------------------------------------------------------------------------
if __name__=="__main__":
    search_file =sys.argv[1]

    if not(search_file.split('.')[0]+'.pickle' in glob.glob('*.pickle')):
        start =time.time()
        vecsea.indexer() #user defined file to create a dictionary based index 
        stop =time.time()
        print ("Index time:",'{0:.5f}'.format((stop- start)/60),"mins")

    try:
        ques_file =sys.argv[2:]
        start =time.time()
        run(ques_file)
        stop =time.time()
        #print(stop-start)
    except:
        print("We could'nt find a match !!")

#------------------------------------------------------------------------------------
