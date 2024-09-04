import ctypes
import logging
import os
import time
from datetime import date
import snscrape.modules.twitter as sntwitter
from selenium import webdriver
from selenium.common import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger()


def generate_retweet_like(fileTweet, fileRetweet, selectedDate):
    # Récupération des utilisateurs avec leurs tweets
    usersWithTweets = get_tweets_by_user(fileTweet, selectedDate)
    usersRetweet = get_users(fileRetweet)
    if (len(usersWithTweets) != 0) and (len(usersRetweet) != 0):
        # Lancement du bot
        tBot = Twitterbot()
        # Chaque utilisateur
        for userRetweet in usersRetweet:
            # va se connecter
            logger.info(userRetweet.email + " login")
            tBot.login(userRetweet)
            # pour aller liker et tweeter
            for i, u in enumerate(usersWithTweets):
                # chaque tweet des autres utilisateurs
                if userRetweet.username != u.username:
                    for tweetURL in u.tweetsList:
                        logger.info(tweetURL)
                        tBot.like_retweet(tweetURL)
            logger.info(userRetweet.email + " logout")
            tBot.logout()
            time.sleep(6)
    return usersWithTweets


class User:
    username = ""
    email = ""
    password = ""

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password
        self.tweetsList = []


def get_users(filePath) -> []:
    users = []
    if not os.path.exists(filePath):
        ctypes.windll.user32.MessageBoxW(0,
                                         "Le fichier csv des utilisateurs Twitter est introuvable.",
                                         "Erreur")
        return users
    with open(filePath) as f:
        for line in f.readlines():
            try:
                userSplit = line.split(";")
                users.append(User(userSplit[0].replace("@", ""), userSplit[1], userSplit[2]))
            except ValueError:
                logger.error('Add username, email and password in twitter users file')
                exit(0)
    return users


def get_tweets_by_user(filePath, selectedDate) -> []:
    print(selectedDate)
    if selectedDate is None:
        selectedDate = date.today()
    usersWithTweets = get_users(filePath)
    if (len(usersWithTweets) != 0):
        for indexUser, u in enumerate(usersWithTweets):
            logger.info(u.username)
            try:
                scraperTwitter = sntwitter.TwitterProfileScraper(u.username)
                for indexTweet, tweet in enumerate(scraperTwitter.get_items()):
                    # if tweet.date.date() != date.today():
                    # if indexTweet >= 1:
                    if tweet.date.date() == selectedDate:
                        logger.info(tweet.url)
                        u.tweetsList.append(tweet.url)
                if (len(u.tweetsList) == 0):
                    logger.info("Aucun tweet pour " + u.username)
            except Exception as e:
                logger.error("Twitter get_tweets_by_user : " + str(e))
                pass
    return usersWithTweets


def get_elements() -> []:
    elements = []
    # reading the text file
    # for elements
    file = f"{os.getcwd()}/Configuration/twitterelements.txt"
    if not os.path.exists(file):
        ctypes.windll.user32.MessageBoxW(0,
                                         "Le fichier twitterelements.txt est introuvable dans le dossier de ODIM\\Configuration.",
                                         "Erreur")
        return elements
    with open(file) as f:
        # iterating over the lines
        for line in f.readlines():
            try:
                elements.append(line)
            except ValueError:
                logger.error('Add the WebElements of Twitter in elements file')
                exit(0)
    return elements


class TwitterElements:
    values = get_elements()
    emailInput = (By.CSS_SELECTOR, values[0])
    usernameInput = (By.CSS_SELECTOR, values[1])
    passwordInput = (By.CSS_SELECTOR, values[2])
    nextButton = (By.CSS_SELECTOR, values[3])
    messageInput = (By.CSS_SELECTOR, values[4])
    tweetButton = (By.CSS_SELECTOR, values[5])
    likeButton = (By.CSS_SELECTOR, values[6])
    retweetButton = (By.CSS_SELECTOR, values[7])
    confirmRetweetButton = (By.CSS_SELECTOR, values[8])
    search = (By.CSS_SELECTOR, values[9])
    profil = (By.CSS_SELECTOR, values[10])
    logoutButton = (By.CSS_SELECTOR, values[11])
    confirmLogout = (By.CSS_SELECTOR, values[12])


class Twitterbot:
    timeout = 300  # seconds

    def __init__(self):
        # initializing chrome
        chrome_options = Options()
        chrome_path = ChromeDriverManager().install()
        chrome_service = Service(chrome_path)

        # adding the path to the chrome driver and
        # integrating chrome_options with the bot
        self.bot = webdriver.Chrome(options=chrome_options, service=chrome_service)

    def login(self, user=User):
        # Page de connexion
        self.bot.get('https://twitter.com/login')
        try:
            # Saisi de l'email
            email = WebDriverWait(self.bot, self.timeout).until(EC.element_to_be_clickable(TwitterElements.emailInput))
            time.sleep(5)
            email.send_keys(user.email)
            next = self.bot.find_element(*TwitterElements.nextButton)
            time.sleep(5)
            next.click()
        except TimeoutException:
            pass
        try:
            # Saisi du nom d'utilisateur OCCASIONNELLEMENT
            username = WebDriverWait(self.bot, 10).until(EC.element_to_be_clickable(TwitterElements.usernameInput))
            time.sleep(5)
            username.send_keys(user.username)
            next = self.bot.find_element(*TwitterElements.nextButton)
            time.sleep(5)
            next.click()
        except TimeoutException:
            pass
        try:
            # Saisi du mot de passe
            time.sleep(5)
            password = WebDriverWait(self.bot, 10).until(
                EC.element_to_be_clickable(TwitterElements.passwordInput))
            time.sleep(5)
            password.send_keys(user.password)
        except TimeoutException:
            pass
        WebDriverWait(self.bot, self.timeout).until(EC.element_to_be_clickable(TwitterElements.messageInput))
        time.sleep(5)

    def logout(self):
        profil = WebDriverWait(self.bot, self.timeout).until(EC.element_to_be_clickable(TwitterElements.profil))
        time.sleep(5)
        profil.click()
        logoutButton = WebDriverWait(self.bot, self.timeout).until(
            EC.element_to_be_clickable(TwitterElements.logoutButton))
        time.sleep(5)
        logoutButton.click()
        confirmLogout = WebDriverWait(self.bot, self.timeout).until(
            EC.element_to_be_clickable(TwitterElements.confirmLogout))
        time.sleep(5)
        confirmLogout.click()



    def like_retweet(self, url):
        # Page du tweet
        self.bot.get(url)
        logger.info(url)
        WebDriverWait(self.bot, self.timeout).until(EC.element_to_be_clickable(TwitterElements.search))
        time.sleep(2)
        try:
            # Recherche du bouton Like et le cliquer
            like = self.bot.find_elements(*TwitterElements.likeButton)[0]
            logger.info("LIKE")
            like.click()
            time.sleep(2)
        except (IndexError, ElementClickInterceptedException):
            logger.error("PAS LIKE")
            pass
        try:
            # Recherche du bouton Retweet et le cliquer
            retweet = self.bot.find_elements(*TwitterElements.retweetButton)[0]
            retweet.click()
            time.sleep(2)
        except (IndexError, ElementClickInterceptedException):
            logger.error("PAS RETWEET")
            pass
        try:
            # Recherche du bouton Retweet simple et le cliquer
            confirmRetweet = self.bot.find_elements(*TwitterElements.confirmRetweetButton)[0]
            logger.info("RETWEET")
            confirmRetweet.click()
            time.sleep(2)
        except (IndexError, ElementClickInterceptedException):
            logger.error("PAS RETWEET SIMPLE")
            pass

    def tweet(self, media=None):
        message = "Hello World !"
        messageInput = WebDriverWait(self.bot, self.timeout).until(
            EC.element_to_be_clickable(TwitterElements.messageInput))
        messageInput.send_keys(message)
        time.sleep(5)
        sendTweet = self.bot.find_element(*TwitterElements.tweetButton)
        sendTweet.click()
