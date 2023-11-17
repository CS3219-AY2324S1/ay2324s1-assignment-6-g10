from typing import List, Optional, Tuple
import requests
from html.parser import HTMLParser
import os
import zipfile
import json


class CfParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.mkdown_data = ""
        self.categories = []
        self.searching = False
        self.testcase = False
        self.problemsetting=False
        self.io_text = []
        self.tag = []
        self.input_bool = False
        self.input_text = ""
        self.output_text = ""
        self.input = []
        self.output = []
        self.ul_ol_container = []
        self.last_removed_tag = ""
        self.tempData = ""
        self.inlineContainers = set(["span", "br", "ol", "ul"])

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        self.tag.append((tag, attrs))
        curr_tag = self.tag[-1]
        if not self.searching:
            if self.checkClass(self.tag[-1], "div", "class", "problem-statement"):
                self.searching = True
        else:
            if (tag == "img"):
                for attr in attrs:
                    if attr[0] == "src":
                        self.tempData += f"\n![]({attr[1]})"
                        break
            elif self.checkClass(curr_tag, "div", "class", "title"):
                self.problemsetting=True
            elif self.checkClass(curr_tag, "div", "class", "input"):
                self.input_bool = True
                self.testcase = True
            elif self.checkClass(curr_tag, "div", "class", "output"):
                self.input_bool = False
                self.testcase = True
            elif self.checkClass(curr_tag, "ul"):
                self.tempData += "\n"
                self.ul_ol_container.append(["ul", "-"])
            elif self.checkClass(curr_tag, "ol"):
                self.tempData += "\n"
                self.ul_ol_container.append(["ol", 0])

            elif self.checkClass(curr_tag, "div", "class", "input-specification"):
                self.tempData += "\n\n------\n"
            elif self.checkClass(curr_tag, "div", "class", "test-example-line"):
                return
            elif self.checkClass(curr_tag, "div"):
                self.tempData += "\n"
            elif self.checkClass(curr_tag, "p"):
                self.tempData += "\n\n"

    def handle_endtag(self, tag: str) -> None:
        self.last_removed_tag = self.tag.pop()
        if not self.searching:
            return
        
        if self.checkClass(self.last_removed_tag, "div", "class", "header"):
                self.problemsetting=False
        elif self.checkClass(self.last_removed_tag, "div", "class", "problem-statement"):
            self.searching = False
        elif self.checkClass(self.last_removed_tag, "div", "class", "property-title"):
            self.tempData += ": "
        elif self.checkClass(self.last_removed_tag, "div", "class", "header"):
            self.tempData += "\n\n------\n"
        elif self.checkClass(self.last_removed_tag, "pre"):
            if self.testcase:
                testdata = "\n".join(self.io_text)
                if self.input_bool:
                    self.input.append(testdata)
                else:
                    self.output.append(testdata)
                
                self.mkdown_data += "\n```\n" + testdata +"\n```\n"
                self.io_text = []
                self.testcase = False
        elif self.checkClass(self.last_removed_tag, "ul"):
            self.ul_ol_container.pop()
        elif self.checkClass(self.last_removed_tag, "ol"):
            self.ul_ol_container.pop()

        if self.last_removed_tag[0] not in self.inlineContainers:
            if self.tempData:
                self.mkdown_data += self.tempData
                self.tempData = ""

    def handle_data(self, data: str) -> None:
        if not self.searching:
            if len(self.tag) and self.checkClass(self.tag[-1], "span", "class", "tag-box"):
                self.categories.append(data.strip())
            return
        if self.checkClass(self.tag[-1], "div", "class", "title"):
            if self.testcase:
                self.tempData += f"\n#### {data} \n----\n"
            else:
                self.tempData += f"\n### {data}\n"
                if self.problemsetting:
                    self.title = data
        elif self.checkClass(self.tag[-1], "div", "class", "section-title"):
            self.tempData += f"\n#### {data}\n"
        else:
            data = data.replace("$", "\\$")
            data = data.replace("*", "\\*")

            if self.checkClass(self.tag[-1], "pre"):
                if self.testcase:
                    self.io_text.append(data.strip())
                else:
                    self.mkdown_data += data.strip()

            elif self.checkClass(self.tag[-1], "div", "class", "test-example-line"):
                self.io_text.append(data.strip())
            else:
                if not data.strip():
                    self.tempData += "\n"
                    return
                data = data.replace("\\$\\$\\$", "$")

                if self.checkClass(self.tag[-1], "li"):
                    if self.last_removed_tag[0] not in self.inlineContainers:
                        if self.ul_ol_container[-1][0] == "ul":
                            delimeter = "- "
                        else:
                            self.ul_ol_container[-1][1] += 1
                            delimeter = f"{self.ul_ol_container[-1][1]}. "
                        self.tempData += "\n"+"  " * \
                            (len(self.ul_ol_container)-1) + delimeter
                    elif self.last_removed_tag[0] in ["ul", "ol"]:
                        self.tempData += "\n\n"+"  " * \
                            (len(self.ul_ol_container))

                if self.checkClass(self.tag[-1], "a"):
                    for prop in self.tag[-1][1]:
                        if prop[0] == "href" and prop[1]:
                            data = f"[{data}]({prop[1]})"

                if self.checkClass(self.tag[-1], "span", "class", "tex-font-style-bf"):
                    data = f"**{data}**"

                self.tempData += data

    def clearData(self):
        self.__init__()

    def toJson(self):
        topics, score = self.categories[:-1], int(self.categories[-1][1:])
        with zipfile.ZipFile(f"testcases.zip", "w") as zf:
            for i in range(len(self.input)):
                zf.writestr(f"{i}.in", self.input[i])
                zf.writestr(f"{i}.out", self.output[i])
        return {
            "question": json.dumps({
                    "title": self.title,
                    "topics": topics,
                    "difficulty": round(min(score + 250 ,3500) / 3500 * 10,1),
                    "input": self.input,
                    "output": self.output,
                    "description": self.mkdown_data
                })
            }, "testcases.zip"

    @staticmethod
    def checkClass(data: Tuple[str, List[Tuple[str, Optional[str]]]],
                   checkTag: str,
                   checkAttr: Optional[str] = None,
                   checkData: Optional[str] = None
                   ) -> bool:
        tag, attrs = data
        splitclass = False
        if tag != checkTag:
            return False
        if checkAttr == None:
            return True
        
        splitclass = checkAttr == 'class'
        for attr in attrs:
            if attr[0] == checkAttr and attr[1] == checkData:
                return True
            if splitclass and attr[0] == checkAttr:
                if checkData in attr[1].split():
                    return True
        return False
    
def submitToServer(data, file: str):
    url = "http://peerprep-g10.com:8080/api/questions"
    res = requests.post(url, files={"testcases": open(file, "rb")}, data=data)
    if res.status_code > 300:
        print(f"Error: {res.status_code} {res.text}")
        return False
    return True


def mkfolder_exist(path: str) -> str:
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def questionLetterGenerator():
    for i in range(65, 91):
        Letter = chr(i)
        result = yield Letter
        if result:
            continue
        additional_addon = ["1", "2", "3", "4", "5", "6", "7"]
        for j in additional_addon:
            result = yield Letter+j
            if not result:
                if j == additional_addon[0]:
                    yield ""
                    return
                break

def scrapeContest(event, context, verbosity = 0):
    contestlower, contestupper = event["contestlower"], event["contestupper"]
    ROOT_DIR = "https://codeforces.com/problemset/problem/{}/{}"
    contestsGenerator = range(contestlower, contestupper)

    p = CfParser()
    if verbosity > 0:
        print("Verbosity mode is on")

    for contest in contestsGenerator:
        lettergen = questionLetterGenerator()
        Question = next(lettergen)
        while Question:
            if verbosity:
                print(f"Collecting {contest}/{Question} from CodeForces.com...")
            res = requests.get(ROOT_DIR.format(contest, Question), allow_redirects=False)
            if (res.status_code != 200):
                if verbosity > 1:
                    print(f"{contest}/{Question} does not exist on this question. Moving on...")
                Question = lettergen.send(False)
                continue
            if 'application/pdf' in res.headers.get("Content-Type"):
                if verbosity > 1:
                    print(f"{Question} is a pdf, skipping...")
                continue
            p.feed(res.content.decode('UTF-8'))
            dat, file = p.toJson()
            res = submitToServer(dat, file)
            os.remove(file)
            if (res and verbosity):
                print(f"Successfully submitted {contest}/{Question} to server")

            p.clearData()
            Question = lettergen.send(True)
        
        if verbosity:
            print(f"finish collecting questions on contest {contest}")

        return {
            "statusCode": 200,
            "body": "Successfully submitted all questions to server"
        }
