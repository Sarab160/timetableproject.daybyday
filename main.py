from pprint import pprint
from datetime import datetime,timedelta
import json
import customtkinter as ctk
from tkinter import filedialog
from tkinter import messagebox
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
    global timetable ,teacher_usage,room_usage,selected_classes,break_period
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
    
    try:
        start_time = start_time_input.get()
        duration = int(duration_input.get())
        break_period = int(break_period_input.get() or 3)
    except:
        output.configure(text="Invalid start time, duration, or break period.")
        return
    
    if break_period not in periods:
        output.configure(text=f"Break period must be between {periods[0]} and {periods[-1]}")
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

#pdf code

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
def export_pdf(timetable, selectedClasses, break_period):
    if not timetable or not selectedClasses:
        output.configure(text="❌ Please generate the timetable first.")
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf")],
        initialfile=f"Timetable_{'_'.join(selectedClasses)}.pdf",
        title="Save Timetable PDF"
    )

    if not file_path:
        messagebox.showerror("Error","❌ PDF export cancelled.")
        return

    try:
        user_start_time = start_time_input.get() or "08:00"
        user_duration = int(duration_input.get() or "45")
    except:
        messagebox.showerror("Error","Invalid start time or duration")
        return

    pdf = TimetablePDF('L', 'mm', 'A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    total_width = 270  
    col_width = total_width / (len(periods) + 1)
    row_height = 18
    time_slots = [time_slot(p, user_start_time, user_duration) for p in periods]

    for cls in selectedClasses:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, f"Timetable for Class {cls}", ln=True, align="C")
        pdf.ln(2)

        pdf.set_font("Arial", 'B', 10)
        pdf.cell(col_width, row_height, "Day/Time", border=1, align='C')
        for slot in time_slots:
            pdf.cell(col_width, row_height, slot, border=1, align='C')
        pdf.ln()

        for day in days:
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(col_width, row_height, day, border=1, align='C')

            for p in periods:
                slot = timetable[cls][day][p]
                x = pdf.get_x()
                y = pdf.get_y()

                if p == break_period:
                    pdf.set_font("Arial", 'B', 9)
                    pdf.multi_cell(col_width, row_height, "Break", border=1, align='C')
                    pdf.set_xy(x + col_width, y)
                    continue

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

    try:
        pdf.output(file_path)
        messagebox.showinfo(text=f"✅ PDF saved to: {file_path}")
    except Exception as e:
        output.configure(text=f"❌ Failed to save PDF: {str(e)}")


#Reset button code 
def clear_timetable_display():
    output.configure(text="")  
    output_textbox.configure(state="normal")  
    output_textbox.delete("1.0", "end")    
    output_textbox.configure(state="disabled") 

##Gui
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")
app=ctk.CTk()
app.geometry("1000x750")
app.title("TimelyAI")

home_frame=ctk.CTkFrame(app)
setup_frame=ctk.CTkFrame(app)
timetable_fame=ctk.CTkFrame(app)
info_frame=ctk.CTkFrame(app)
teacher_frame=ctk.CTkFrame(app)
class_frame=ctk.CTkFrame(app)
subjects_frame=ctk.CTkFrame(app)
room_frame=ctk.CTkFrame(app)
frames=[setup_frame,timetable_fame,home_frame,info_frame,teacher_frame,room_frame,class_frame,subjects_frame]

def showframe(frame):
    for f in frames:
        f.place_forget()
    frame.place(relwidth=1, relheight=1)
    
spacer = ctk.CTkFrame(home_frame, height=100, fg_color="transparent")
h_button_config = {
    "font": ctk.CTkFont(size=20, weight="bold"),
    "corner_radius": 12,
    "width": 250,
    "height": 60,
    "fg_color": "#007BFF",        
    "hover_color": "#0056d2",     
    "border_color": "#0056d2",    
 
}
button_config = {
    "font": ctk.CTkFont(size=14, weight="bold"),
    "corner_radius": 10,
    "width": 200,
    "height": 45,
    "fg_color": "#007BFF",        
    "hover_color": "#0056d2",     
    "border_color": "#0056d2", 
}

ctk.CTkLabel(setup_frame,text="Setup TimeTable",font=("Arial",20,"bold")).pack(pady=10)
ctk.CTkLabel(home_frame, text="⏰ TimelyAI 🤖", font=ctk.CTkFont(size=30, weight="bold"), text_color="white").pack(pady=10)


ctk.CTkLabel(home_frame,text="Home Page",font=ctk.CTkFont(size=15, weight="bold"), text_color="white").pack(pady=0,padx=10)

spacer.pack()
spacer.pack()
spacer.pack()
spacer.pack()
button_container = ctk.CTkFrame(home_frame, fg_color="transparent")
button_container.pack(pady=(40,10))
setup_button = ctk.CTkButton(button_container, text="📅 Setup Timetable", command=lambda: showframe(setup_frame),**h_button_config)
setup_button.pack(pady=10)

ctk.CTkLabel(setup_frame, text="Enter Classes (comma separated):").pack(pady=5)
class_input = ctk.CTkEntry(setup_frame, placeholder_text="A,B,C", width=400)
class_input.pack(pady=5)

ctk.CTkLabel(setup_frame, text="Start Time (HH:MM):").pack(pady=5)
start_time_input = ctk.CTkEntry(setup_frame, placeholder_text="08:00", width=200)
start_time_input.pack(pady=5)

ctk.CTkLabel(setup_frame, text="Lecture Duration (minutes):").pack(pady=5)
duration_input = ctk.CTkEntry(setup_frame, placeholder_text="45", width=200)
duration_input.pack(pady=5)

ctk.CTkLabel(setup_frame, text="Break Period Number (e.g., 3):").pack(pady=5)
break_period_input = ctk.CTkEntry(setup_frame, placeholder_text="3", width=200)
break_period_input.pack(pady=5)

load_subject_btn = ctk.CTkButton(setup_frame, text="📚 Load Subjects", command=lambda: subject_entites(class_input.get().split(",")),**button_config)
load_subject_btn.pack(pady=10)

subject_frame = ctk.CTkScrollableFrame(setup_frame, height=200, width=950)
subject_frame.pack(pady=10)

ctk.CTkButton(setup_frame, text="⬅️ Back to Home", command=lambda: showframe(home_frame),**button_config).pack(pady=10)

generatetime_btn = ctk.CTkButton(button_container, text="⚙️ Generate Timetable", command=lambda:showframe(timetable_fame),**h_button_config)
generatetime_btn.pack(pady=10)

ctk.CTkLabel(timetable_fame,text="⚙️ Generate Timetable and Export as Pdf",font=("Aial",20,"bold")).pack(pady=10)

generate_btn = ctk.CTkButton(timetable_fame, text="⚙️ Generate Timetable", command=generate_timable,**button_config)
generate_btn.pack(pady=10)

export_pdf_btn = ctk.CTkButton(
    timetable_fame,
    text="📄 Export as PDF",
    command=lambda: export_pdf(timetable, selected_classes,break_period),**button_config
)

export_pdf_btn.pack(pady=10)

reset_display_btn = ctk.CTkButton(timetable_fame, text="❌ Clear Timetable Display", command=clear_timetable_display,**button_config)
reset_display_btn.pack(pady=10)

output = ctk.CTkLabel(timetable_fame, text="")
output.pack()

output_textbox = ctk.CTkTextbox(timetable_fame, width=950, height=400, font=("Courier", 12))
output_textbox.pack(pady=10)
output_textbox.configure(state="disabled")
ctk.CTkButton(timetable_fame, text="⬅️ Back to Home", command=lambda: showframe(home_frame),**button_config).pack(pady=10)





# details of data

def show_teachers_data():
    # Clear previous content in findroute_frame
    for widget in teacher_frame.winfo_children():
        widget.destroy()

    ctk.CTkLabel(teacher_frame, text="All Teachers Info", font=("Arial", 16, "bold")).pack(pady=10)

    scroll_frame = ctk.CTkScrollableFrame(teacher_frame, width=760, height=460)
    scroll_frame.pack(padx=10, pady=5, fill="both", expand=True)

    for tid, info in teacher.items():
        frame = ctk.CTkFrame(scroll_frame)
        frame.pack(pady=5, padx=10, fill="x")

        name = info.get("name", "N/A")
        subjects_str = ", ".join(info.get("subjects", []))
        unavailable = ", ".join(info.get("preferences", {}).get("unavailable_days", []))

        ctk.CTkLabel(frame, text=f"ID: {tid} | Name: {name}", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        ctk.CTkLabel(frame, text=f"Subjects: {subjects_str}").pack(anchor="w", padx=20)
        ctk.CTkLabel(frame, text=f"Unavailable Days: {unavailable if unavailable else 'None'}").pack(anchor="w", padx=20)

    ctk.CTkButton(teacher_frame, text="⬅️ Back to Details", command=lambda: showframe(info_frame),**button_config).pack(pady=10)

def show_class_data():
    # Clear previous content in findroute_frame
    for widget in class_frame.winfo_children():
        widget.destroy()

    ctk.CTkLabel(class_frame, text="All Teachers Info", font=("Arial", 16, "bold")).pack(pady=10)

    scroll_frame = ctk.CTkScrollableFrame(class_frame, width=760, height=460)
    scroll_frame.pack(padx=10, pady=5, fill="both", expand=True)

    for tid, info in classes.items():
        frame = ctk.CTkFrame(scroll_frame)
        frame.pack(pady=5, padx=10, fill="x")

        name = info.get("name", "N/A")
        subjects_str = ", ".join(info.get("subjects", []))
        

        ctk.CTkLabel(frame, text=f"=> {tid} | Class Name: {name}", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        ctk.CTkLabel(frame, text=f"Subjects: {subjects_str}").pack(anchor="w", padx=20)
        

    ctk.CTkButton(class_frame, text="⬅️ Back to Details", command=lambda: showframe(info_frame),**button_config).pack(pady=10)

def show_subject_data():
    # Clear previous content in subject_frame
    for widget in subjects_frame.winfo_children():
        widget.destroy()

    # 🔘 Heading
    ctk.CTkLabel(subjects_frame, text="📘 All Subject Information", font=("Arial", 18, "bold")).pack(pady=10)

    # 🔃 Scrollable section
    scroll_frame = ctk.CTkScrollableFrame(subjects_frame, width=760, height=460)
    scroll_frame.pack(padx=10, pady=5, fill="both", expand=True)

    for sub_id, info in subject.items():
        frame = ctk.CTkFrame(scroll_frame)
        frame.pack(pady=5, padx=10, fill="x")

        # Extract type
        sub_type = info.get("type", "N/A")

        # Duration
        dur_raw = info.get("duration", "N/A")
        duration = ", ".join(map(str, dur_raw)) if isinstance(dur_raw, (list, tuple)) else str(dur_raw)

        # Weekly lectures
        lect_raw = info.get("weekly_lectures", "N/A")
        lectures = ", ".join(map(str, lect_raw)) if isinstance(lect_raw, (list, tuple)) else str(lect_raw)

        
        ctk.CTkLabel(frame, text=f"=> {sub_id}  |  Type: {sub_type}", font=("Arial", 13, "bold")).pack(anchor="w", padx=10)
        ctk.CTkLabel(frame, text=f" Lecture Duration: {duration}", font=("Arial", 11)).pack(anchor="w", padx=20)
        ctk.CTkLabel(frame, text=f" Weekly Lectures: {lectures}", font=("Arial", 11)).pack(anchor="w", padx=20)

    ctk.CTkButton(subjects_frame, text="⬅️ Back to Details Page", command=lambda: showframe(info_frame), **button_config).pack(pady=10)


def show_rooms_data():
    for widget in room_frame.winfo_children():
        widget.destroy()

    ctk.CTkLabel(room_frame, text="All Rooms Info", font=("Arial", 16, "bold")).pack(pady=10)

    scroll_frame = ctk.CTkScrollableFrame(room_frame, width=760, height=460)
    scroll_frame.pack(padx=10, pady=5, fill="both", expand=True)

    theory_rooms = room.get("normal_rooms", [])
    lab_rooms = room.get("lab_rooms", [])

    # Display theory rooms
    theory_frame = ctk.CTkFrame(scroll_frame)
    theory_frame.pack(pady=5, padx=10, fill="x")
    ctk.CTkLabel(theory_frame, text="=> Normal Rooms:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
    ctk.CTkLabel(theory_frame, text=", ".join(theory_rooms)).pack(anchor="w", padx=20)

    # Display lab rooms
    lab_frame = ctk.CTkFrame(scroll_frame)
    lab_frame.pack(pady=5, padx=10, fill="x")
    ctk.CTkLabel(lab_frame, text="=> Lab Rooms:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
    ctk.CTkLabel(lab_frame, text=", ".join(lab_rooms)).pack(anchor="w", padx=20)

    ctk.CTkButton(room_frame, text="⬅️ Back to Details page", command=lambda: showframe(info_frame),**button_config).pack(pady=10)




ctk.CTkButton(button_container, text="👨‍🏫 Show Teachers Info", command=lambda: [show_teachers_data(), showframe(teacher_frame)],**h_button_config).pack(pady=10)
ctk.CTkButton(button_container, text="🏷️ Show Classes Info", command=lambda: [show_class_data(), showframe(class_frame)],**h_button_config).pack(pady=10)
ctk.CTkButton(button_container, text="📚 Show Subjects Info", command=lambda: [show_subject_data(), showframe(subjects_frame)],**h_button_config).pack(pady=10)
ctk.CTkButton(button_container, text="🏢 Show Rooms Info", command=lambda: [show_rooms_data(), showframe(room_frame)],**h_button_config).pack(pady=10)

showframe(home_frame)
app.mainloop()
