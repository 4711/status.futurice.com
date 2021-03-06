""" This script fetches information from RT 
(http://bestpractical.com/rt/) mysql database. It works at least with RT 
3.8. """

from time import time
import json
import MySQLdb
import logging
import datetime
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import urllib2

import rt_settings

class RTStats:
    def __init__(self):
        self.username = rt_settings.RT_USERNAME
        self.password = rt_settings.RT_PASSWORD
        self.database = rt_settings.RT_DATABASE
        self.upload_url = rt_settings.UPLOAD_URL
        self.upload_password = rt_settings.UPLOAD_PASSWORD
        self._db = None
        register_openers()

    @property
    def db(self):
        """ Saves database connection instance and automatically 
            connects if connection is not yet initialized """
        if self._db is None:
            self._db = self.connect()
        return self._db

    def connect(self):
        """ Connect to database. Missing error handling """
        logging.debug("Opening database connection")

        return MySQLdb.connect(passwd=self.password, 
                               db=self.database,
                               user=self.username)

    def send_data(self, name, data):
        """ Saves data to name.data.json and sends it to 
            rt_settings.UPLOAD_URL """
        filename = name+".data.json"
        logging.debug("send_data with key", name, "filename", filename)
        data_dump = json.dumps({"name": name, "data": data})
        open(filename, "w").write(data_dump)
        datagen, headers = multipart_encode({"data": open(filename, "rb"), "password": self.upload_password, "what": name+".json"})
        request = urllib2.Request(self.upload_url, datagen, headers)
        urllib2.urlopen(request).read()

    def run(self):
        """ get all statistics """
        self.get_ticket_stats()

    def get_ticket_stats(self):
        """ Get statistics for tickets """

        def get_one(query):
            """ Execute query and return first column of first row """
            logging.debug("get_one with query", query)
            cursor = self.db.cursor()
            cursor.execute(query)
            (count,) = cursor.fetchone()
            return count

        def get_two_all(query):
            """ Execute query and return all rows as dictionary """
            logging.debug("get_two_all with query", query)
            cursor = self.db.cursor()
            cursor.execute(query)
            items = cursor.fetchall()
            ret = {}
            for name, count in items:
                ret[name] = count
            
            return ret
            

        data = {}
        # total number of tickets, including automatic
        data["all_tickets"] = get_one("SELECT COUNT(*) AS c FROM Tickets;")
        # total number of tickets with unique subject
        data["all_tickets_unique"] = get_one("SELECT COUNT(DISTINCT Subject) AS c FROM Tickets;")

        dates = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        xtitles = [a for a in range(0, 24)]

        data["dots"] = {}

        for item, query in [("all", "SELECT DATE_FORMAT(Created, '%%H') AS timestamp, COUNT(*) AS c FROM Tickets WHERE DATE_FORMAT(Created, '%%a')='%s' GROUP BY timestamp;"), 
                          ("manual", "SELECT DATE_FORMAT(Created, '%%H') AS timestamp, COUNT(*) AS c FROM Tickets WHERE Queue=1 AND DATE_FORMAT(Created, '%%a')='%s' GROUP BY timestamp;"), 
                    ("all_resolved", "SELECT DATE_FORMAT(Resolved, '%%H') AS timestamp, COUNT(*) AS c FROM Tickets WHERE DATE_FORMAT(Resolved, '%%a')='%s' GROUP BY timestamp;"),
                 ("manual_resolved", "SELECT DATE_FORMAT(Resolved, '%%H') AS timestamp, COUNT(*) AS c FROM Tickets WHERE Queue=1 AND DATE_FORMAT(Resolved, '%%a')='%s' GROUP BY timestamp;")]:
            data["dots"][item] = {}
            data["dots"][item]["ytitles"] = dates
            data["dots"][item]["xtitles"] = []

            for hour in xtitles:
                tmp3 = str(hour).strip()
                if len(tmp3) == 1:
                    tmp3 = "0"+tmp3
                data["dots"][item]["xtitles"].append(tmp3)
            data["dots"][item]["date_stats"] = []

            for day in dates:
                tmp = get_two_all(query % day)
                for xtitle in xtitles:
                    tmp3 = str(xtitle).strip()
                    if len(tmp3) == 1:
                        tmp3 = "0"+tmp3
                    data["dots"][item]["date_stats"].append(tmp.get(tmp3, None))
            data["dots"][item]["date_stats"] = data["dots"][item]["date_stats"][-3:] + data["dots"][item]["date_stats"][:-3]

        # number of unique subjects
        data["unique_manual"] = get_one("SELECT COUNT(distinct(Subject)) AS c FROM Tickets WHERE Queue=1;")
        for daterange in ["7", "30", "365"]:
            data["unique_manual_%sd" % daterange] = get_one("SELECT COUNT(DISTINCT Subject) AS c FROM Tickets WHERE Created >= DATE_SUB(current_date, INTERVAL %s day) AND Queue=1;" % daterange)

        dayranges = ["7", "30", "365"]
        datenames = ["Created", "Resolved"]
        variable_name = [("hour", "%H"), ("day", "%a")]
        for datename in datenames:
            for (vbn, vbn_f) in variable_name:
                data["%s_per_%s" % (datename.lower(), vbn)] = get_two_all("SELECT DATE_FORMAT(%s, '%%%s') AS timestamp, COUNT(*) AS c FROM Tickets WHERE Queue=1 GROUP BY timestamp;" % (datename, vbn_f))
                for dayrange in dayranges:
                    data["%s_per_%s_%sd" % (datename.lower(), vbn, dayrange)] = get_two_all("SELECT DATE_FORMAT(%s, '%%%s') AS timestamp, COUNT(*) AS c FROM Tickets WHERE Queue=1 AND %s >= DATE_SUB(current_date, INTERVAL %s day) GROUP BY timestamp;" % (datename, vbn_f, datename, dayrange))

        # general tickets per day
        dictlist = [("created_futu", 
            get_two_all("SELECT DATE_FORMAT(Tickets.Created, '%j') AS timestamp, COUNT(*) AS c FROM Tickets, Users WHERE Tickets.Created >= DATE_SUB(current_date, INTERVAL 120 day) AND Tickets.Creator=Users.id AND Users.EmailAddress like '%.%@futurice.com' AND Users.EmailAddress not in ('phaser@futurice.com', 'mailman@futurice.com', 'noreply@futurice.com', 'zabbix@futurice.com') GROUP BY timestamp;")
         ), ("created_other",
            get_two_all("SELECT DATE_FORMAT(Tickets.Created, '%j') AS timestamp, COUNT(*) AS c FROM Tickets, Users WHERE Tickets.Created >= DATE_SUB(current_date, INTERVAL 120 day) AND Tickets.Creator=Users.id AND Users.EmailAddress not like '%@%futurice.com' GROUP BY timestamp;")
         ), ("created_machine",
            get_two_all("SELECT DATE_FORMAT(Tickets.Created, '%j') AS timestamp, COUNT(*) AS c FROM Tickets, Users WHERE Tickets.Created >= DATE_SUB(current_date, INTERVAL 120 day) AND Tickets.Creator=Users.id AND (Users.EmailAddress like '%@%.futurice.com' or Users.EmailAddress in ('zabbix@futurice.com', 'mailman@futurice.com', 'noreply@futurice.com')) GROUP BY timestamp;")
         ), ("resolved_futu",
            get_two_all("SELECT DATE_FORMAT(Tickets.Resolved, '%j') AS timestamp, COUNT(*) AS c FROM Tickets, Users WHERE Tickets.Resolved >= DATE_SUB(current_date, INTERVAL 120 day) AND Tickets.Creator=Users.id AND Users.EmailAddress like '%.%@futurice.com' AND Users.EmailAddress not in ('phaser@futurice.com', 'mailman@futurice.com', 'noreply@futurice.com', 'zabbix@futurice.com') GROUP BY timestamp;")
         ), ("resolved_other",
            get_two_all("SELECT DATE_FORMAT(Tickets.Resolved, '%j') AS timestamp, COUNT(*) AS c FROM Tickets, Users WHERE Tickets.Resolved >= DATE_SUB(current_date, INTERVAL 120 day) AND Tickets.Creator=Users.id AND Users.EmailAddress not like '%@%futurice.com' GROUP BY timestamp;")
         ), ("resolved_machine",
            get_two_all("SELECT DATE_FORMAT(Tickets.Resolved, '%j') AS timestamp, COUNT(*) AS c FROM Tickets, Users WHERE Tickets.Resolved >= DATE_SUB(current_date, INTERVAL 120 day) AND Tickets.Creator=Users.id AND (Users.EmailAddress like '%@%.futurice.com' or Users.EmailAddress in ('zabbix@futurice.com', 'mailman@futurice.com', 'noreply@futurice.com')) GROUP BY timestamp;")
        )]

        final_workflow = {"max": 0, "buckets": [], "authors": {
            "0": {"c": 0, "n": "Created by employees", "d": 0, "u": 0},
            "1": {"c": 0, "n": "Created by external", "d": 0, "u": 0},
            "2": {"c": 0, "n": "Created by machine", "d": 0, "u": 0},
            "3": {"c": 0, "n": "Employee ticket resolved", "d": 0, "u": 0},
            "4": {"c": 0, "n": "External ticket resolved", "d": 0, "u": 0},
            "5": {"c": 0, "n": "Machine ticket resolved", "d": 0, "u": 0}
        }}
        date_translations = {}
        current_date = int(datetime.date.today().strftime("%j"))
        date_translations[current_date] = 0
        count = 0
        counttemp = 0
        for numbers in range(current_date, 0, -1):
            counttemp += 1
            if counttemp % 7 == 0:
                count = count - 1
            date_translations[numbers] = count
        for numbers in range(366, current_date, -1):
            counttemp += 1
            if counttemp % 7 == 0:
                count = count - 1
            date_translations[numbers] = count

        list_temp = {}
        value_counters = [0, 0, 0, 0, 0, 0]
        name_value_table = {"created_futu": 0, "created_other": 1, "created_machine": 2, "resolved_futu": 3, "resolved_other": 4, "resolved_machine": 5}
        for (name, items) in dictlist:
            for item in items:
                itemnum = date_translations[int(item)]
                if not list_temp.get(itemnum):
                    list_temp[itemnum] = {}
                if not list_temp.get(itemnum).get(name):
                    list_temp[itemnum][name] = 0
                list_temp[itemnum][name] += items.get(item)
                value_counters[name_value_table.get(name)] += items.get(item)
        for key in sorted(list_temp.iterkeys()):
            values_temp = list_temp.get(key)
            values = []
            for item in values_temp:
                if values_temp.get(item) > final_workflow["max"]:
                    final_workflow["max"] = values_temp.get(item)
                values.append([name_value_table[item], values_temp.get(item)])
            # sort values from highest to lowest
            values.sort(key=lambda x: x[1])
            final_workflow["buckets"].append({"d": int(time() + 7 * 86400 * (1 + key)), "i": values})

        counter = 0
        for item in value_counters:
            final_workflow["authors"][str(counter)]["c"] = item
            counter += 1

        # distribution of subject occurance
        data["subject_occurance"] = get_two_all("SELECT c AS occurance, COUNT(*) AS count FROM (select COUNT(*) AS c FROM Tickets WHERE Queue=1 GROUP BY Subject) AS Subjects GROUP BY c;")

        data["workflow"] = final_workflow

        data["open_tickets"] = get_one("SELECT COUNT(*) AS c FROM Tickets WHERE (status='open' AND (Queue=1 AND Type!='reminder'));")
        data["new_tickets"] = get_one("SELECT COUNT(*) AS c FROM Tickets WHERE (status='new' AND (Queue=1 AND Type!='reminder'));")

        cursor = self.db.cursor()
        cursor.execute("SELECT COUNT(*) AS c FROM Users WHERE EmailAddress like '%.%@futurice.com';")
        (futurice_users, ) = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) AS c FROM Users WHERE EmailAddress not like '%.%@futurice.com';")
        (other_users, ) = cursor.fetchone()
        data["other_users"] = other_users
        data["futurice_users"] = futurice_users
        cursor.close()
        self.send_data("ittickets", data)


def main():
    """ Run and save """
    rtstats = RTStats()
    rtstats.run()

if __name__ == '__main__':
    main()
