import PyPDF2

def getPdf(file_name):    #returns a list of strings with each string being contents of a page
    def getPage(page_no):
        page = pdf_obj.getPage(page_no)
        page_content = ''
        for page_list in page.extractText().split("\n"):
            page_content = page_content + page_list.strip()+' '  #using strip to get rid of unnecessary spaces(if present)
        return page_content

    pdf_list = []
    pdf_obj = PyPDF2.PdfFileReader(file_name)
    for i in range(0,pdf_obj.getNumPages()-30):
        pdf_list.append(getPage(i))
    return pdf_list
