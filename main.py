from pprint import pprint
from datetime import datetime,timedelta
import json
import customtkinter as ctk
from tkinter import filedialog

from fpdf import FPDF
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
    global timetable ,teacher_usage,room_usage,selected_classes
    selected_classes=class_input.get().split(",")
    selected_classes=[cls.strip( ) for cls in selected_classes if cls.strip() in classes]
    
    if not selected_classes:
        output.configure(text="Please Entry valid class Names. ")
        return
    
    
    
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
    
class TimetablePDF(FPDF):
    def header(self):
        self.ln(8)  # Add spacing at the top

    def footer(self):
        self.set_y(-12)
        self.set_font("Arial", 'I', 9)
        self.set_text_color(100)
        now = datetime.now().strftime("%d-%b-%Y %I:%M %p")
        self.cell(0, 10, f"Generated by TimelyAI on {now}", 0, 0, 'C')

# Export function
def export_pdf(timetable, selectedClasses):
    file_path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf")],
        initialfile=f"Timetable_{'_'.join(selectedClasses)}.pdf",
        title="Save Timetable PDF"
    )

    if not file_path:
        output.configure(text="❌ PDF export cancelled.")
        return

    try:
        user_start_time = start_time_input.get() or "08:00"
        user_duration = int(duration_input.get() or "45")
    except:
        output.configure(text="❌ Invalid start time or duration.")
        return

    pdf = TimetablePDF('L', 'mm', 'A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    total_width = 270  
    col_width = total_width / (len(periods) + 1)  # +1 for day column
    row_height = 18
    time_slots = time_slot(user_start_time, user_duration, len(periods))

    for cls in selectedClasses:
        # Centered title
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, f"Timetable for Class {cls}", ln=True, align="C")
        pdf.ln(2)

        # Header row
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(col_width, row_height, "Day/Time", border=1, align='C')
        for slot in time_slots:
            pdf.cell(col_width, row_height, slot, border=1, align='C')
        pdf.ln()

        # Content rows
        for day in days:
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(col_width, row_height, day, border=1, align='C')

            for p in periods:
                slot = timetable[cls][day][p]
                x = pdf.get_x()
                y = pdf.get_y()

                if slot:
                    subject = slot["subject"]
                    teacher = slot["teacher"]
                    room = slot["room"]
                    pdf.set_font("Arial", 'B', 9)
                    pdf.multi_cell(col_width, 5, subject, border=1, align='C')
                    pdf.set_xy(x, pdf.get_y())
                    pdf.set_font("Arial", '', 8)
                    pdf.multi_cell(col_width, 4.5, f"{teacher}\n{room}", border=0, align='C')
                    pdf.set_xy(x + col_width, y)
                else:
                    pdf.set_font("Arial", '', 9)
                    pdf.multi_cell(col_width, row_height, "Free", border=1, align='C')
                    pdf.set_xy(x + col_width, y)

            pdf.ln(row_height)

        pdf.add_page()

    pdf.output(file_path)
    output.configure(text=f"✅ PDF saved to: {file_path}")
##Gui
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")
app=ctk.CTk()
app.geometry("1000x750")
app.title("TimelyAI")

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
export_pdf_btn = ctk.CTkButton(
    app,
    text="Export as PDF",
    command=lambda: export_pdf(timetable, selected_classes)
)
export_pdf_btn.pack(pady=10)

output = ctk.CTkLabel(app, text="")
output.pack()

output_textbox = ctk.CTkTextbox(app, width=950, height=300, font=("Courier", 12))
output_textbox.pack(pady=10)
output_textbox.configure(state="disabled")

app.mainloop()
