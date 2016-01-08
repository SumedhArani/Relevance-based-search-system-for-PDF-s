import sys
import pickle
import nltk
from nltk.corpus import stopwords
from pgreader import getPdf

class para:
    para_no =0 #paragraph/page number
    def __init__(self):
        self.__class__.para_no +=1 #static variable
        self.keywords ={} #keywords in paragraph
        self.para_vect ={} #mapping words as vector
        
    def add_word(self,word):
        #Dictionary- Key:"(Word,paragraph number)" Value:"count"
        if (word, self.para_no) not in self.keywords:
            self.keywords[(word,self.para_no)]=1
        else:
            self.keywords[(word,self.para_no)]+=1            
#---------------------------------------------------------------------------
index_dict ={} #dictionary mapping the whole pdf/document key:"first 3 letter" value:"(word,paranumber)"
vector_doc =[None] #List of lists containing wc and sum info of each page
porter =nltk.PorterStemmer() #NLTK algo to stem words
common_text =stopwords.words('english1') #Self created list of stopwords
#-------------------------------------------------------------------------
def map_vector(new_para):
    #para_vect - dict -> Key:"word" Value:"word count"
    for x in new_para.keywords:
        new_para.para_vect[x[0]]= new_para.keywords[x] 
    new_para.para_vect['#SUM']=sum([(new_para.para_vect[y]) for y in new_para.para_vect])
    vector_doc.append(new_para.para_vect) #vector_doc contains info about all pages in the doc
#--------------------------------------------------------------------------
def index(string):
    new_para =para() #calling the constructor
    text =nltk.wordpunct_tokenize(string) #tokenising the string
    sorted_text =[p.lower() for p in text] #making lower case to make data case-insensitive
    sorted_text.sort()
    [new_para.add_word(w) for w in sorted_text if w.isalpha() and len(w)>2] #check if it is a word
    stop_text =[(x,new_para.para_no) for x in common_text] #list of stopwords
    terms =list(set(new_para.keywords)-set(stop_text)) #list of unique terms in the page: all terms- common terms
    temp ={}
    for term in terms:
        temp[term] =new_para.keywords[term] #removing common words from intial keywords dictionary
    new_para.keywords = temp
    for x in new_para.keywords:
        #To speed up search, min 3 letters to be entered during search
        if x[0][0:3] not in index_dict:
            index_dict[x[0][0:3]] = [x] #mapping words to a dict that contains info about whole pdf
        else:
            index_dict[x[0][0:3]].append(x)
    map_vector(new_para) #function call to map_vector of that page
#-------------------------------------------------------------------------
def indexer():
    #read the file and create the index 
    file_name =sys.argv[1]
    try:
        f =open(file_name,'r')
        doc = f.read().split('\n\n')
        f.close()
    except:
        doc =getPdf(file_name)

    #Index page/para by page/para
    for each_para in doc:
        index(each_para)
        
    #Dump the index data in a pickle file(Serialization of data)
    fout =open('{0}.pickle'.format(sys.argv[1].split('.')[0]),'wb')
    pickle.dump(index_dict, fout)
    fout.close()

    #Dump the vector data in an another pickle file(Serialization of data)
    fvec =open('{0}_vec.pickle'.format(sys.argv[1].split('.')[0]),'wb')
    pickle.dump(vector_doc, fvec)
    fvec.close()

#------------------------------------------------------------------------
if __name__ =="__main__":
    indexer()
