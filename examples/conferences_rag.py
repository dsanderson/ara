import project as proj
import utils
import extractor
import collector


project = proj.Project('Conference Speaker RAG')

t1 = project.add_task([], utils.echo('Mechanical engineering conferences in the US'))
t2 = project.add_task([t1], collector.query_google())
t3 = project.add_task([t2], collector.get_urls_from_query(), produce_many=True)
t4 = project.add_task([t3], collector.scrape_url_to_cache())
t5 = project.add_task([t4], extractor.RAG('Please provide a list of every conference named in the document, with a semicolon (;) between each conference.  If no conferences are named, answer "none".  Be as concise as possible.'))
t6 = project.add_task([t5], extractor.partition_data("none"), collect_all=True, produce_many=True)
t7 = project.add_task([t6], utils.split_text(';', clean=True), produce_many=True)
t8 = project.add_task([t7], utils.template_text('{} talks 2023'))
t9 = project.add_task([t8], collector.query_google())
t10 = project.add_task([t9], collector.get_urls_from_query(), produce_many=True)
t11 = project.add_task([t10], collector.scrape_url_to_cache())
t12 = project.add_task([t11], extractor.RAG('Please return the speaker names, affiliations and talk description for any talks related to AI or ML in the document.  If the document does not contain any talks, answer "none".  Be as concise as possible.'))
t13 = project.add_task([t12], extractor.partition_data("none"), collect_all=True, produce_many=True)

if __name__=="__main__":
    project.work()