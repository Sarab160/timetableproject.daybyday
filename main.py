from pprint import pprint
from datetime import datetime,timedelta
import json

with open("teachers.json") as t:
    teacher=json.load(t)

with open("rooms.json") as r:
    room=json.load(r)

with open("subject.json") as s:
    subject=json.load(s)

with open("classes.json") as c:
    classes=json.load(c)

days=["Monday","Tuesday","Wednesday","Thursday","Friday"]
periods=[1,2,3,4,5,6]
start_time="08:00"

select_classes=input("Enter class names to generate time table ,comma seperated: ").split(",")
select_classes=[cls.strip() for cls in select_classes if cls.strip() in classes]

input={}

for cls in select_classes:
    input[cls]={
        "subjects":{},
        "break_period":3,
        "lecture_duration":45
    }
    for sub in classes[cls]["subjects"]:
        for teacher_id,teacher_info in teacher.items():
            if sub.lower() in [s.lower() for s in teacher_info["subjects"]]:
                is_lab=subject[sub].get("type","Theory").lower=="lab"
                roomlist=room["lab_rooms"] if is_lab else room["normal_rooms"]
                input[cls]["subjects"][sub]={
                    "teacher":teacher_id,
                    "room":roomlist[0]
                }
                break

timetable= {
    class_name: {
        day:{
            period:None for period in periods} for day in days
        }
    for class_name in input
    }

room_usage={
    room_id:{day:{
        period: False for period in periods} for day in days}
    for room_id in room["normal_rooms"] + room["lab_rooms"]
}

teacher_usage={
    tid:{day:
        {period:False for period in periods} for day in days}
    for tid in teacher
}

def teacher_availble(tid,day,period):
    return not teacher_usage[tid][day][period]

def room_available(rid,day,period):
    return not room_usage[rid][day][period]

def mark_usage(tid,rid,day,period):
    teacher_usage[tid][day][period]=True
    room_usage[rid][day][period]=True
    
def time_slot(perionnumber,start=start_time,duration=45):
    base=datetime.strptime(start_time,"%H:%M")
    start=base + timedelta(minutes=(perionnumber-1)* duration)
    end=start +timedelta(minutes=duration)
    return f"{start.strftime("%I:%M %p")} - {end.strftime("%I:%M %p")}"

def lectures(className,subjectName,teacherid,roomid,totallecture,breakperiod,duration):
    assigned=0
    for day in days:
        for period in periods:
            if period ==breakperiod:
                continue
            if timetable[className][day][period] is None and teacher_availble(teacherid,day,period) and room_available(roomid,day,period):
                timetable[className][day][period]={
                    "subject":subjectName,
                    "teacher":teacher[teacherid]["name"],
                    "room":roomid,
                    "time":time_slot(period,duration =duration)
                }
                mark_usage(teacherid,roomid,day,period)
                assigned+=1
                if assigned ==totallecture:
                    return True
    return False

def assign_labs(className,subjectName,teacherid,roomid,totallabs,breakperiod,duration):
    assigned=0
    for day in days:
        for period in range(1,5):
            if breakperiod in [period,period+1,period+2]:
                continue
            if all(
                timetable[className][day][p] is None and 
                teacher_availble(teacher_id,day,p)and
                room_available(roomid,day,p)
                for p in [period,period+1,period+2]
            ):
                start_time=time_slot(period,duration=duration).split(" - ")[0]
                end=datetime.strptime(start_time, "%I:%M %p") + timedelta(minutes=duration*3)
                Range=f"{start_time}- {end.strftime("%I:%M %p")}"
                
            
                for p in [period,period+1,period+2]:
                    timetable[className][day][p]={
                        "subject":subjectName,
                        "teacher":teacher[teacherid]["name"],
                        "room":roomid,
                        "time":Range
                    }
                    mark_usage(teacherid,roomid,day,p)
                assigned+=1
                if assigned==totallabs:
                    return True
    return False

for className, info in input.items():
    for sub,detail in info["subjects"].items():
        subtype=subject[sub]["type"]
        lercture_perweek=subject[sub].get("weekly_lectures",3)
        duration =info.get("lecture_duration",45)
        
        if subtype.lower()=="lab":
            assign_labs(className,sub,detail["teacher"],detail["room"],lercture_perweek,info["break_period"],duration)
        else:
            lectures(className,sub,detail["teacher"],detail["room"],lercture_perweek,info["break_period"],duration)

for cls in select_classes:
    print("Timetable for class {cls}: ")
    pprint(timetable[cls])
    
print("generated")
