from pprint import pprint
from datetime import datetime,timedelta
import json
import customtkinter as ctk

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

subjects={}
timetable={}
teacher_usage={}
room_usage={}

def time_slot(perionnumber,start_time,duration=45):
    base=datetime.strptime(start_time,"%H:%M")
    start=base + timedelta(minutes=(perionnumber-1)* duration)
    end=start +timedelta(minutes=duration)
    return f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}"


def teacher_availble(tid,day,period):
    return not teacher_usage[tid][day][period]

def room_available(rid,day,period):
    return not room_usage[rid][day][period]

def mark_usage(tid,rid,day,period):
    teacher_usage[tid][day][period]=True
    room_usage[rid][day][period]=True

def assigne_lecture(className,subjectName,teacher_id,total_lecture, break_period,duration, start_time):
    assigned=0
    isLab=subject[subjectName]["type"].lower()=="lab"
    roomList=room["lab_rooms"] if isLab else room["normal_rooms"]
    lab_duration=duration*3 if isLab else duration
    
    for day in days:
        if day in teacher[teacher_id]["preferences"].get("unavailable_days",[]):
            continue
        
        if isLab:
            for period in range(1,5):
                if break_period in [period,period+1,period+2]:
                    continue
            for room_id in roomList:
                if all(
                   timetable[className][day][p] is None and teacher_availble(teacher_id,day,p) and
                   room_available(room_id,day,p)
                   for p in [period,period+1,period+2]
                ):
                    start_time_str=time_slot(period,start_time,duration,).split(" - ")[0]
                    endTime=datetime.strptime(start_time_str,"%I:%M %p") + timedelta(minutes=lab_duration)
                    time_range=f"{start_time_str} - {endTime.strftime("%I:%M %p")}"
                    
                    for p in [period,period+1,period+2]:
                        timetable[className][day][p] ={
                            "subject":subjectName+" (lab) ",
                            "teacher":teacher[teacher_id]["name"],
                            "room":room_id,
                            "time":time_range
                        }
                        mark_usage(teacher_id,room_id,day,p)
                    assigned+=1
                    if assigned==total_lecture:
                        return True
    else:
        
        for day in days:
            if day in teacher[teacher_id]["preferences"].get("unavailable_days", []):
                continue
            for period in periods:
                if period == break_period:
                    continue

            for room_id in roomList:
                if timetable[className][day][period] is None and teacher_availble(teacher_id,day,period) and room_available(room_id,day,period):
                    timetable[className][day][period] ={
                            "subject":subjectName,
                            "teacher":teacher[teacher_id]["name"],
                            "room":room_id,
                            "time":time_slot(period,start_time,duration)
                        }
                    mark_usage(teacher_id,room_id,day,period)
                    assigned+=1
                    break
            if assigned == total_lecture:
                return True
    return False

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")
app=ctk.CTk()
app.geometry("1000x750")
app.title("TimelyAI")

def subject_entites(selected_classes):
    for widget in subject_frame.winfo_children():
        widget.destroy()
    subjects.clear()

    for cls in selected_classes:
        class_subjects = classes[cls]["subjects"]
        for sub in class_subjects:
            matched_sub = next((k for k in subject if k.lower() == sub.lower()), sub)
            row_frame = ctk.CTkFrame(subject_frame)
            row_frame.pack(pady=5, fill="x", padx=10)

            ctk.CTkLabel(row_frame, text=f"{cls} - {matched_sub}", width=250).pack(side="left", padx=5)

            teacher_combo = ctk.CTkOptionMenu(row_frame, values=[tid for tid, tinfo in teacher.items() if matched_sub.lower() in [s.lower() for s in tinfo["subjects"]]])
            teacher_combo.pack(side="left", padx=5)

            subjects[(cls, matched_sub)] = {
                "teacher": teacher_combo
            }

def generate_timable():
    selected_classes=class_input.get().split(",")
    selected_classes=[cls.strip( ) for cls in selected_classes if cls.strip() in classes]
    
    if not selected_classes:
        output.configure(text="Please Entry valid class Names. ")
        return
    
    global timetable ,teacher_usage,room_usage
    
    timetable={
    cls:{day:{
        p: None for p in periods
    } for day in days} for cls in selected_classes
}

    teacher_usage={
        tid:{day:{
            p: False for p in periods
        } for day in days} for tid in teacher
    }
    
    room_usage={
        rid:{day:{
            p: False for p in periods
        } for day in days} for rid in room["normal_rooms"] + room["lab_rooms"]
        
    }
    
    break_period=3
    try:
        start_time=start_time_input.get()
        duration=int(duration_input.get())
    except:
        output.configure(text="Invalid start time or duration")
        return
    
    for (cls,sub),widgets in subjects.items():
        tid=widgets["teacher"].get()
        
        matched_sub=next((key for key in subject if key.lower()==sub.lower()),None)
        
        if tid and matched_sub:
            subType=subject[matched_sub]["type"].lower()
            
            if subType=="lab":
                lecture=1
            else:
                lecture=subject[matched_sub].get("weekly_lectures",3)
                
            assigne_lecture(cls,matched_sub,tid,lecture,break_period,duration,start_time)
        else:
            print(f" skip {sub} - subject not matched or teacher not selected.")
            
    result=""
    for cls in selected_classes:
        result+=f"Timetabel for clas{cls}: "
        for day in days:
            result+=f"{day}"
            for period in periods:
                slot=timetable[cls][day][period]
                if slot:
                    result+=f"   period {period}: {slot["subject"]} ({slot["teacher"]}) in {slot["room"]} [{slot["time"]}]\n"
                else:
                    result+=f"   period {period}: free\n"
    
    output_textbox.configure(state="normal")
    output_textbox.delete("1.0", "end")
    output_textbox.insert("end", result)
    output_textbox.configure(state="disabled")
    
ctk.CTkLabel(app, text="Enter Classes (comma separated):").pack(pady=5)
class_input = ctk.CTkEntry(app, placeholder_text="A,B,C", width=400)
class_input.pack(pady=5)

ctk.CTkLabel(app, text="Start Time (HH:MM):").pack(pady=5)
start_time_input = ctk.CTkEntry(app, placeholder_text="08:00", width=200)
start_time_input.pack(pady=5)

ctk.CTkLabel(app, text="Lecture Duration (minutes):").pack(pady=5)
duration_input = ctk.CTkEntry(app, placeholder_text="45", width=200)
duration_input.pack(pady=5)

load_subject_btn = ctk.CTkButton(app, text="Load Subjects", command=lambda: subject_entites(class_input.get().split(",")))
load_subject_btn.pack(pady=10)

subject_frame = ctk.CTkScrollableFrame(app, height=200, width=950)
subject_frame.pack(pady=10)

generate_btn = ctk.CTkButton(app, text="Generate Timetable", command=generate_timable)
generate_btn.pack(pady=10)

output = ctk.CTkLabel(app, text="")
output.pack()

output_textbox = ctk.CTkTextbox(app, width=950, height=300, font=("Courier", 12))
output_textbox.pack(pady=10)
output_textbox.configure(state="disabled")

app.mainloop()
