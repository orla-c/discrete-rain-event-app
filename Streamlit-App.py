import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from io import StringIO

# defining the function needed 

def split(df, group):
     gb = df.groupby(group)
     return [gb.get_group(x) for x in gb.groups]



st.title("Generate Discrete Rainfall Event File")
st.subheader("Please upload the continuous rainfall event .red file")

uploaded_file = st.file_uploader("Choose a file", type = ".red")
if uploaded_file is not None:

    stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
    string = stringio.read()

    # make the string created a list that we can use
    list_data = [row.split(", ") for row in string.split("\n")]
    flat_list = [item for sublist in list_data for item in sublist]

    
    #find date
    date = str.split(flat_list[3])[1][0:8]
    date = date[:2] + "-" + date[2:4] + "-" + date[4:]

    # find time
    time = str.split(flat_list[3])[1][8:]
    time = time[:2] + ":" + time[2:4] + ":" + time[4:6]

    # find timestep field
    timestep = str.split(flat_list[3])[2]

    # number of profiles
    no_profiles = str.split(flat_list[3])[3]


    # find the column names
    col_names = []
    start = 5
    for i in range(int(no_profiles)):
        col_names.append(flat_list[start][:24])
        start += 3


    # find the column names
    col_names = []
    start = 5
    for i in range(int(no_profiles)):
        col_names.append(flat_list[start][:24])
        start += 3
    

    option_list = ["----"]
    for i in range(len(col_names)):
        option_list.append(col_names[i])

    option = st.selectbox(
    'What profile would you like to look at?',
    (option_list))



    if option == "----":
        st.write("No Profile Selected")

    else:
        with st.spinner("Loading - Takes around 20 minutes"):
            # find rainfall values
            rain_vals = []
            for row in flat_list[22:]:
                #rain_vals.append(row.split("   "))
                rain_vals.append(row.split(" "))
            # (tidying it up)
            for x in rain_vals:
                del x[0]

            rain_vals = [list(filter(None, lst)) for lst in rain_vals]

            # make the rainfall dataframe
            rainfall_df = pd.DataFrame(rain_vals, columns=col_names)
            rainfall_df = rainfall_df[:-2]


            # every 12 rows = 1 hour
            # start at -1 so it counts the first 60 minutes as hour 0
            hour_number = -1
            hour_no = []

            for row,col in rainfall_df.iterrows():
                if row % 12 == 0:
                    hour_number +=1
                hour_no.append(hour_number)

            rainfall_df["no. Hours Since Start"] = hour_no

            date_and_time = date + " " + time
            start_time = date_and_time
            date_time = []
            for i in range(rainfall_df.shape[0]):
                date_time.append(datetime.strptime(start_time, '%d-%m-%Y %H:%M:%S') + timedelta(minutes = 5*i))

            rainfall_df["Date/Time"] = date_time

            # find where there's rain in each SAAR column
            rain_event_df = {}
            for col in col_names:
                rain_event = []
                for row in rainfall_df[col]:
                    if row != "0.000":
                        rain_event.append("True")
                    else:
                        rain_event.append("False")

                set_rain_df = rainfall_df[[col, "Date/Time"]]
                set_rain_df["Rain"] = rain_event
                rain_event_df[col] = set_rain_df


            # find the rain event number
            for col in col_names:
                event_number_col = []
                event_number = 1

                # could maybe change the value to app user input instead of just looking for rainfall events lasting at least 1 hour
                hour_check = list(range(0,12))

                for index, vals in enumerate(rain_event_df[col]['Rain']):
                    check_event = [x+index for x in hour_check]

                    if any(rain_event_df[col]['Rain'][check_event[0]:check_event[-1]] == "True"):
                        if index >= 1:
                            if event_number_col[index - 1] == "Not a Rain Event":
                                event_number +=1

                        event_number_col.append(event_number)
                    else:
                        event_number_col.append("Not a Rain Event")
                
                rain_event_df[col]["Event Number"] = event_number_col


            # find the events that have at least an hours worth of rain
            event_df_final = {}
            for col in col_names:
                big_event_number = 1
                big_event_number_col = []
                og_event_number = []

                for num in rain_event_df[col]["Event Number"].unique():
                    og_event_number.append(num)
                    how_many_5_mins_each_event = len(rain_event_df[col][(rain_event_df[col]['Event Number']==num) & (rain_event_df[col]['Rain']=='True')])
                    if how_many_5_mins_each_event >= 12:

                        big_event_number_col.append(big_event_number)
                        big_event_number += 1


                    else:
                        big_event_number_col.append("Not a Big Event")

                big_event_df = pd.DataFrame(list(zip(og_event_number, big_event_number_col)), columns=["Event Number", "Big Event Number"])

                event_df_final[col] = pd.merge(rain_event_df[col], big_event_df, on = "Event Number" )
            


            st.dataframe(event_df_final[option][[option,'Date/Time']], use_container_width=True)

        with open("discrete_rain_profile.red", "w", encoding="utf-8") as f:

            remove_no_rain_rows_df = event_df_final[option][event_df_final[option]['Big Event Number'] != "Not a Big Event"]
            grouped_event = remove_no_rain_rows_df.groupby(remove_no_rain_rows_df['Big Event Number'])
            
            for group in grouped_event:
                f.write(flat_list[0][:29])
                # change encoding to UTF8 (idk i'm just guessing its that)
                f.write("UTF8")
                f.write("\n")
                f.write(flat_list[2][:31])
                # find event number
                f.write(str(f'{group[0]:04d}'))
                f.write("\n")

                # writng the date/ time of the start of each event
                f.write(flat_list[3][:6])
                for time in group[1]['Date/Time']:
                    time_string = [str(time)[8:10], str(time)[5:7],  str(time)[0:4], str(time)[11:13], str(time)[14:16], str(time)[17:19]]
                    time_string_fixed =  ''.join(time_string)
                    f.write(time_string_fixed)
                    break
                f.write("  ")
                
                f.write(flat_list[3][22:25])
                f.write("        1")
                f.write(flat_list[3][34:])
            

                #f.write("\n")
                f.write(flat_list[4])
                #f.write("\n")

                
                f.write(str(event_df_final[option].columns[0]))
                f.write("                                        ")
                f.write(str(event_df_final[option].columns[0]))
                f.write("\n")
                f.write("     1.000     1.000")
                f.write("\n")
                
                for element in group[1][option]:
                    f.write("\t")
                    f.write(str(element))
                    f.write("\n")
                    
                f.write("END")
                f.write("\n")
            
        with open("discrete_rain_profile.red", "rb") as file:
            st.download_button(label="Download the .red file for discrete rain events", data=file,  file_name='discrete_rain_profile.red')

            


            
