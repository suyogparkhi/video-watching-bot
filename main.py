import requests
import sys
import config
from loguru import logger


class Skipera:
    def __init__(self, course):
        self.user_id = None
        self.course_id = None
        self.base_url = config.BASE_URL
        self.session = requests.Session()
        self.session.headers.update(config.HEADERS)
        self.session.cookies.update(config.COOKIES)
        self.course = course
        if not self.get_user_id():
            self.login()

    def login(self):
        logger.debug("Attempting login")
        response = self.session.post(
            self.base_url + "login/v3",
            json={
                "code": "",
                "email": config.EMAIL,
                "password": config.PASSWORD,
                "webrequest": True,
            }
        )
        logger.info(response.content)

    def get_user_id(self):
        response = self.session.get(self.base_url + "adminUserPermissions.v1?q=my").json()
        try:
            self.user_id = response["elements"][0]["id"]
            logger.info("User ID: " + self.user_id)
        except KeyError:
            if "errorCode" in response:
                logger.error("Error: " + response["errorCode"])
            return False
        return True

    def get_modules(self):
        response = self.session.get(
            self.base_url + f"onDemandCourseMaterials.v2/?q=slug&slug={self.course}&includes=modules"
        ).json()
        self.course_id = response["elements"][0]["id"]
        logger.debug("Course ID: " + self.course_id)
        logger.debug("Modules Count: " + str(len(response["linked"]["onDemandCourseMaterialModules.v1"])))
        for module in response["linked"]["onDemandCourseMaterialModules.v1"]:
            logger.info(module["name"] + " -- " + module["id"])

    def get_items(self):
        response = self.session.get(
            self.base_url + "onDemandCourseMaterials.v2/",
            params={
                "q": "slug",
                "slug": self.course,
                "includes": "passableItemGroups,passableItemGroupChoices,items,tracks,gradePolicy,gradingParameters",
                "fields": "onDemandCourseMaterialItems.v2(name,slug,timeCommitment,trackId)",
                "showLockedItems": "true"
            }
        ).json()
        for video in response["linked"]["onDemandCourseMaterialItems.v2"]:
            logger.info("Accessing: " + video["name"])
            self.watch_item(video["id"])

    def watch_item(self, item_id):
        response = self.session.post(
            self.base_url + f"opencourse.v1/user/{self.user_id}/course/{self.course}/item/{item_id}/lecture/videoEvents/ended?autoEnroll=false",
            json={"contentRequestBody": {}}
        ).json()
        if "contentResponseBody" not in response:
            logger.info("Not a video. Marking as read.")
            self.read_item(item_id)

    def read_item(self, item_id):
        response = self.session.post(
            self.base_url + "onDemandSupplementCompletions.v1",
            json={
                "courseId": self.course_id,
                "itemId": item_id,
                "userId": int(self.user_id)
            }
        )
        if "Completed" not in response.text:
            logger.error("Requires manual completion.")

@logger.catch
def main():
    if len(sys.argv) < 2:
        logger.error("Course slug not provided")
        return

    skipera = Skipera(sys.argv[1])
    skipera.get_modules()
    skipera.get_items()


if __name__ == '__main__':
    main()
