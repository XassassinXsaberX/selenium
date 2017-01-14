from selenium import webdriver
import requests
import threading,re,os,time

class Spider:
    def __init__(self,user_mail,password):
        self.__user_mail = user_mail
        self.__password = password
        self.__header = {'User-Agent' : 'Mozilla/5.0 (X11; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0'}
        self.__web_page = []                                    #放置圖片的網頁(注意不是圖片的來源檔)  ex.  http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60694672
        self.__browser_num = 3                                  #建立多少額外瀏覽器
        self.__other_browser = [0]*self.__browser_num           #存放其他瀏覽器物件
        self.__browser = webdriver.Chrome("chromedriver.exe")   #存放一個瀏覽器物件
        for i in range(self.__browser_num):
            self.__other_browser[i] = webdriver.Chrome("chromedriver.exe")
            #self.__other_browser[i].set_window_position(0,2000)
        self.__cookies = {}   #存放登入的cookie資訊

    def login(self):#登入到pixiv並取的cookie
        url = "https://accounts.pixiv.net/login?lang=zh&source=pc&view_type=page&ref=wwwtop_accounts_index"
        r = requests.Session()                                          #建立一個 session 會話
        r1 = r.get(url,headers=self.__header)                           #先連線到pixiv網頁來獲取post_key  (注意要在同一個session上，不然post_key會跟著改變)
        lt = re.findall(r'post_key[.\W\S\w\s]+?>', r1.text)              #利用正規表示法來找出post_key 並取出來存到value變數中
        value = lt[0].split("value=")[1]
        value = value[1:-2]
        data = {'pixiv_id': self.__user_mail,                             #這是待會要post 出去的表單
                'password': self.__password,
                'post_key' : value
                }
        r2 = r.post("https://accounts.pixiv.net/login?lang=zh&source=pc&view_type=page&ref=wwwtop_accounts_index",data=data, headers=self.__header)
        #post完後代表登入成功，同時我們也可以獲得登入成功後瀏覽器存下的cookie
        self.__cookies = r.cookies.get_dict()

        #將屬性__browser也登錄到pixiv網站上吧
        for i in range(self.__browser_num):
            self.__other_browser[i].get("http://www.pixiv.net/")  # 首先要先用瀏覽器連到，才能添加cookies
            self.__other_browser[i].delete_all_cookies()
            lt = list(self.__cookies.keys())
            for j in range(len(lt)):  # 一個一個添加cookie
                 self.__other_browser[i].add_cookie({'name': lt[j], 'value': self.__cookies[lt[j]]})

    def recommend(self):#到pixiv的推薦頁面並下載十頁圖片
        if len(self.__cookies.keys()) == 0:
            print("尚未登入pixiv....")
        else:
        #因為該頁面是動態變化，所以此時要搭配selenium
            #self.__browser.set_window_position(0,2000)
            self.__browser.get("http://www.pixiv.net/")                     #首先要先用瀏覽器連到某個網站，才能添加cookies
            self.__browser.delete_all_cookies()
            lt = list(self.__cookies.keys())
            for i in range(len(lt)):                                       #一個一個添加cookie
                self.__browser.add_cookie({'name' : lt[i] , 'value' : self.__cookies[lt[i]]})
            self.__browser.get("http://www.pixiv.net/recommended.php")    #現在可以搭配cookie來連到登錄後的recommend頁面
            self.__browser.find_element_by_id('enable-auto-view').click()   #按下網頁的按鈕
            # 因為此網頁有使用javascript動態的變化功能，所以要執行javascript來模擬對網頁的動作
            for i in range(1):  # 進行一次
                self.__browser.execute_script('window.scrollTo(0, document.body.scrollHeight);')  # 重複往下捲動
                time.sleep(1)  # 每次執行打瞌睡一秒
            #print(self.__browser.page_source)

            #接著可以找到放置圖片的網頁，我們將該網頁的url取出來，之後再利用該url進行下載
            web_lt = re.findall(r'<li class="image-item">[.\w\W\s\S]+?"[.\w\W\s\S]+?"',self.__browser.page_source)
            for i in range(len(web_lt)):
                web_lt[i] = web_lt[i].split('<a href="')[1]
                web_lt[i] = 'http://www.pixiv.net/' + web_lt[i][:-1]
                self.__web_page.append(web_lt[i])

            thread = [0]*self.__browser_num  #建立self.__browser_num個thread來平行加速下載
            i=0
            while True:
                if i >= len(web_lt) :
                    break
                if i % self.__browser_num == 0 and i>0 :
                    for j in range(self.__browser_num):
                        thread[j].join()

                thread[i % self.__browser_num] = threading.Thread(target=self.download_image,args=(web_lt[i],i%self.__browser_num))
                thread[i % self.__browser_num].start()
                i+=1

    def download_image(self,url,i):
        self.__other_browser[i].get(url)
        #先建立一個資料夾來存放圖片
        if not os.path.isdir("pixiv_picture"):
            os.mkdir("pixiv_picture")

        #接下來要注意圖片可能為"插畫"或"漫畫"，所以會分不同狀況來處理(目前尚不處理動圖、小說)
        #以下為處理插畫的流程
        if 'class="_layout-thumbnail ui-modal-trigger"' in self.__other_browser[i].page_source:
            #self.__other_browser[i].find_element_by_xpath('//div[@class="_layout-thumbnail ui-modal-trigger"]').click()   #按下圖片執行javascript使網頁發生變化
            
            lt = re.findall(r'class="original-image"[.\w\W\s\S]+?original[.\w\W\s\S]+?"',self.__other_browser[i].page_source)
            source_url = lt[0].split('src="')[1]
            source_url = source_url[:-1]                       #這就是原始圖片的連結
            for i in range(len(source_url)-1,-1,-1):           #接下來決定圖片的檔名
                if source_url[i] == '/':
                    image_name = source_url[i+1:]
                    break
            self.__header['Referer'] = url
            r = requests.get(source_url,cookies=self.__cookies,headers=self.__header)
            with open('pixiv_picture/'+image_name,"wb") as f:
                f.write(r.content)

         #以下為處理漫畫的流程
        elif 'class="_layout-thumbnail"' in self.__other_browser[i].page_source:
            #再創建一個資料夾來放漫畫
            #首先決定資料夾名稱
            lt = re.findall(r'illust_id=[0-9]+&?',url)
            image_num = lt[0][10:] #image 為pixiv 圖片的編號
            if image_num[-1]=='&':
                image_num = image_num[:-1]
            dir_name = 'pixiv_picture/' + image_num
            if not os.path.isdir(dir_name):
                os.mkdir(dir_name)

            #接下來進入漫畫的網頁
            self.__other_browser[i].get('http://www.pixiv.net/member_illust.php?mode=manga&illust_id='+image_num)
            lt = re.findall(r'<div class="item-container"[.\w\W\s\S]+?<img src="[.\w\W\s\S]+?"',self.__other_browser[i].page_source)
            lt[0] = lt[0].split('img src="')[1]
            lt[0] = lt[0][:-1]
            lt2 = lt[0].split("p0")
            for i in range(1,len(lt)):
                lt[i] = lt2[0] + "p{0}".format(i) + lt2[1]
            #現在 lt 儲存了圖片的url

            def parallel_download(url,dir_name,refer):
                header = {'User-Agent' : 'Mozilla/5.0 (X11; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0',
                          'Referer' : refer}
                r = requests.get(url,headers=header)
                #決定圖片名稱
                for i in range(len(url)-1,-1,-1):
                    if url[i] == '/':
                        image_name = url[i+1:]
                        break
                with open(dir_name+'/'+image_name,"wb") as f:
                    f.write(r.content)

            thread = [0]*len(lt)#建立thread來加速下載
            for i in range(len(thread)):
                threading.Thread(target=parallel_download,args=(lt[i],dir_name,'http://www.pixiv.net/member_illust.php?mode=manga&illust_id='+image_num)).start()

        else:
            print("目前尚未能下載此類的圖片")

    def quit(self):
        if hasattr(self,"__browser") :
            self.__browser.quit()
        for i in range(self.__browser_num):
            self.__other_browser[i].quit()



if __name__=='__main__':
    user_mail = "a5083a5083@gmail.com"
    password = 'ab123456789ba'
    spider = Spider(user_mail,password)
    spider.login()
    spider.recommend()
    #spider.download_image("http://www.pixiv.net/member_illust.php?mode=medium&amp;illust_id=60456774&amp;uarea=recommended_illusts_page",0)
    #spider.download_image("http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60799963",0)
    spider.quit()