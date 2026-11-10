import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import xml.dom.minidom
from datetime import datetime, timedelta

st.set_page_config(
    page_title="TLC Course XML Generator",
    page_icon="📅",
    layout="wide"
)

st.title("📅 TLC Course Schedule to Orchard XML Converter")
st.markdown("Upload your corrected course scheduling CSV to convert it into a well-formatted Orchard XML recipe.")

# Sidebar Settings
st.sidebar.header("⚙️ Settings")
start_id = st.sidebar.number_input(
    "Starting Course ID", 
    min_value=1, 
    value=201, 
    step=1, 
    help="The first unique ID used for the Course Identifier sequence."
)
time_offset = st.sidebar.number_input(
    "Time Offset (Hours)", 
    value=0, 
    step=1, 
    help="Adjust times if needed. Set to 0 if the spreadsheet is already correct."
)
author = st.sidebar.text_input("Recipe Author", value="LEGIS\\LISIRAS")
owner = st.sidebar.text_input("Course Owner", value="/User.UserName=LEGIS\\\\LISINCW")
status = st.sidebar.selectbox("Course Status", ["Draft", "Published"], index=0)

uploaded_file = st.file_uploader("Upload your scheduling CSV", type="csv")

def convert_csv_to_xml(df, start_id, time_offset, author, owner, status):
    root = ET.Element("Orchard")
    
    # Recipe metadata
    recipe = ET.SubElement(root, "Recipe")
    export_utc = ET.SubElement(recipe, "ExportUtc")
    export_utc.text = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    author_elem = ET.SubElement(recipe, "Author")
    author_elem.text = author
    is_setup = ET.SubElement(recipe, "IsSetupRecipe")
    is_setup.text = "false"
    
    content = ET.SubElement(root, "Content")
    current_id = start_id
    
    for idx, row in df.iterrows():
        # Clean and combine date and time directly
        dt_str = f"{str(row['Date']).strip()} {str(row['StartTime']).strip()}"
        try:
            # Matches YYYY-MM-DD HH:MM:SS format
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                dt = pd.to_datetime(dt_str)
            except Exception:
                st.error(f"Error parsing date/time at row {idx + 1}: {dt_str}")
                continue
                
        # Optional offset adjust
        if time_offset != 0:
            dt = dt + timedelta(hours=time_offset)
            
        xml_time_str = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        course = ET.SubElement(content, "Course", {
            "Id": f"/Identifier={current_id}",
            "Status": status
        })
        
        ET.SubElement(course, "Course.StartTime", {"Value": xml_time_str})
        ET.SubElement(course, "TextField.Location", {"Text": str(row['Location'])})
        
        # Build description with formatted anchor tag
        desc_html = f'<p><a href="{row["InPersonClass"]}" target="_blank" title="Register for {row["Title"]} Class">Register for {row["Title"]} Class</a></p>\n<p>{row["Description"]}</p>'
        ET.SubElement(course, "TextField.Description", {"Text": desc_html})
        
        now_str = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        ET.SubElement(course, "CommonPart", {
            "Owner": owner,
            "CreatedUtc": now_str,
            "PublishedUtc": now_str,
            "ModifiedUtc": now_str
        })
        ET.SubElement(course, "IdentityPart", {"Identifier": ""})
        ET.SubElement(course, "TitlePart", {"Title": str(row['Title'])})
        
        current_id += 1
        
    raw_xml = ET.tostring(root, encoding='utf-8')
    dom = xml.dom.minidom.parseString(raw_xml)
    return dom.toprettyxml(indent="  ", encoding="utf-8")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        
        st.subheader("📊 CSV Data Preview")
        st.dataframe(df.head(5), use_container_width=True)
        
        # Convert
        xml_data = convert_csv_to_xml(df, start_id, time_offset, author, owner, status)
        
        # Show Preview
        st.subheader("📄 Generated XML Preview (First 1500 Characters)")
        st.code(xml_data[:1500].decode('utf-8') + "\n\n... (Truncated) ...", language="xml")
        
        # Download Button
        st.download_button(
            label="💾 Download XML Recipe",
            data=xml_data,
            file_name="cscweb_nov.xml",
            mime="application/xml"
        )
        st.success("🎉 XML generation complete. Click the button above to download your file!")
    except Exception as e:
        st.error(f"Failed to process file: {e}")
