import os
import urllib
import urllib2
import zipfile
import datetime
import formencode
import BeautifulSoup

from pyramid_simpleform import Form
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render_to_response
from pyramid_simpleform.renderers import FormRenderer

from oerpub.rhaptoslabs import sword2cnx
from oerpub.rhaptoslabs.slideimporter.slideshare import fetch_slideshow_status

from choose import save_cnxml
from utils import check_login, clean_cnxml

class QuestionAnswerSchema(formencode.Schema):
    allow_extra_fields = True
    #question1 = formencode.validators.String()
    #options1 = formencode.validators.String()
    #solution1 = formencode.validators.String()

@view_config(route_name='enhance')
def enhance(request):
    check_login(request)
    session = request.session
    google_resource_id = ""
    slideshare_id = ""
    embed_google = False
    embed_slideshare = False
    not_converted = True
    show_iframe = False
    form = Form(request, schema=QuestionAnswerSchema)
    validate_form = form.validate()
    print form.all_errors()
    if session.has_key('google-resource-id'):
        google_resource_id = session['google-resource-id']
    if session.has_key('slideshare_id'):
        slideshare_id = session['slideshare_id']
        if fetch_slideshow_status(slideshare_id) == "2":
            not_converted = False
            show_iframe = True



    if google_resource_id!="":
        embed_google = True
    if slideshare_id!="":
        embed_slideshare = True
    templatePath = "templates/google_ss_preview.pt"
    if validate_form:
        introductory_paragraphs = request.POST.get('introductory_paragraphs')
        question_count=0
        cnxml=session["cnxml"]+"""<content><section id="intro-section-title"><title id="introtitle">Introduction</title><para id="introduction-1">"""+introductory_paragraphs+"""</para></section><section id="slides-embed"><title id="slide-embed-title">View the slides</title><figure id="ss-embed-figure"><media id="slideshare-embed" alt="slideshare-embed"><iframe src="http://www.slideshare.net/slideshow/embed_code/"""+slideshare_id+"""" width="425" height="355" /></media></figure></section>"""        
        for i in range(1,6):
            form_question = request.POST.get('question-'+str(i))
            if form_question:                
                form_radio_answer = request.POST.get('radio-'+str(i)) #this give us something like 'answer-1-1'. so our solution is this
                question_count +=1                
                if question_count==1:
                    cnxml+="""<section id="test-section"><title>Test your knowledge</title>"""
                itemlist = ""
                for j in range(1,10):
                    try:
                        
                        form_all_answers = request.POST.get('answer-'+str(i)+'-'+str(j))
                        if form_all_answers:
                            itemlist +="<item>" + form_all_answers+"</item>"
                        
                    except:
                        print "No element found"
                
                if form_radio_answer:
                    solution = request.POST.get(form_radio_answer)
                    cnxml+="""<exercise id="exercise-"""+str(i)+""""><problem id="problem-"""+str(i)+""""><para id="para-"""+str(i)+"""">"""+str(form_question)+"""<list id="option-list-"""+str(i)+"""" list-type="enumerated" number-style="lower-alpha">"""+str(itemlist)+"""</list></para></problem>"""
                else:
                    print "ELESE CONDUITION OF radio"
                    solution = request.POST.get('answer-'+str(i)+'-1')
                    cnxml+="""<exercise id="exercise-"""+str(i)+""""><problem id="problem-"""+str(i)+""""><para id="para-"""+str(i)+"""">"""+str(form_question)+"""</para></problem>"""
                print "FORM RADIO ANSWER",form_radio_answer
                print "SOLUTION", solution                
                cnxml+=""" <solution id="solution-"""+str(i)+""""> <para id="solution-para-"""+str(i)+"""">"""+solution+"""</para></solution></exercise>"""
				
					
                """form_solution = request.POST.get('solution-'+str(i))
                all_post_data = {"data":{"options":form_options,"solution":form_solution,"question":form_question}}
                for question in all_post_data:
                    options = all_post_data[question]['options']
                    solution = all_post_data[question]['solution']
                    asked_question = all_post_data[question]['question']
                    optionlist=""
                    for option in options:
                        optionlist+="<item>"+option+"</item>"""
                    #cnxml+="""<exercise id="exercise-"""+str(j)+""""><problem id="problem-"""+str(j)+""""><para id="para-"""+str(j)+"""">"""+str(asked_question)+"""<list id="option-list-"""+str(j)+"""" list-type="enumerated" number-style="lower-alpha">"""+str(optionlist)+"""</list></para></problem>"""
                    #cnxml+=""" <solution id="solution-"""+str(j)+""""> <para id="solution-para-"""+str(j)+"""">"""+solution+"""</para></solution></exercise>"""
                    #j+=1
        metadata = session['metadata']
        if question_count>=1:
            cnxml += "</section></content></document>"
        else:
            cnxml += "</content></document>"
        workspaces = [(i['href'], i['title']) for i in session['collections']]
        metadata_entry = sword2cnx.MetaData(metadata)
        zipped_filepath = session['userfilepath']
        zip_archive = zipfile.ZipFile(zipped_filepath, 'w')
        zip_archive.writestr("index.cnxml",cnxml)
        zip_archive.close()
        conn = sword2cnx.Connection("http://cnx.org/sword/servicedocument",
                                    user_name=session['username'],
                                    user_pass=session['password'],
                                    always_authenticate=True,
                                    download_service_document=True)
        collections = [{'title': i.title, 'href': i.href}
                                  for i in sword2cnx.get_workspaces(conn)]
        session['collections'] = collections
        workspaces = [(i['href'], i['title']) for i in session['collections']]
        session['workspaces'] = workspaces
        with open(zipped_filepath, 'rb') as zip_file:
            deposit_receipt = conn.create(
                col_iri = workspaces[0][0],
                metadata_entry = metadata_entry,
                payload = zip_file,
                filename = 'upload.zip',
                mimetype = 'application/zip',
                packaging = 'http://purl.org/net/sword/package/SimpleZip',
                in_progress = True)
        session['dr'] = deposit_receipt
        session['deposit_receipt'] = deposit_receipt.to_xml()
        soup = BeautifulSoup(deposit_receipt.to_xml())
        data = soup.find("link",rel="edit")
        edit_iri = data['href']
        session['edit_iri'] = edit_iri
        creator = soup.find('dcterms:creator')
        username = session['username']
        email = creator["oerdc:email"]
        url = "http://connexions-oerpub.appspot.com/"
        post_values = {"username":username,"email":email,"slideshow_id":slideshare_id}
        data = urllib.urlencode(post_values)
        google_req = urllib2.Request(url, data)
        google_response = urllib2.urlopen(google_req)
        now_string = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        temp_dir_name = '%s-%s' % (request.session['username'], now_string)
        save_dir = os.path.join(request.registry.settings['transform_dir'],temp_dir_name)
        os.mkdir(save_dir)
        request.session['upload_dir'] = temp_dir_name
        cnxml = clean_cnxml(cnxml)
        save_cnxml(save_dir,cnxml,[])
        return HTTPFound(location=request.route_url('metadata'))
        
        
        #return HTTPFound(location=request.route_url('updatecnx'))


    response = {'form':FormRenderer(form),
                "slideshare_id":slideshare_id,
                "google_resource_id":google_resource_id,
                "embed_google":embed_google,
                "embed_slideshare":embed_slideshare,
                "not_converted": not_converted,
                "show_iframe":show_iframe}
    return render_to_response(templatePath, response, request=request)
