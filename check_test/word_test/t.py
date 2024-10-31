
import win32com.client as win32

# Path to your Word document and the file you want to embed
word_file_path =  r'C:\Users\EDY\Desktop\巡检记录\test\word_test\绍兴文理学院运维巡检记录-20241010.docx'
attachment_file_path = r'C:\Users\EDY\Desktop\巡检记录\test\巡检字段.xlsx'

# Open Word application
word_app = win32.Dispatch("Word.Application")
word_app.Visible = False  # Keep Word invisible

# Open the Word document
doc = word_app.Documents.Open(word_file_path)

# Move to the end of the document
word_app.Selection.EndKey(Unit=6)  # Unit=6 means 'move to the end of the story'

# Insert attachment as an OLE object
word_app.Selection.InlineShapes.AddOLEObject(
    ClassType="",  # Automatically determines the OLE class type based on file extension
    FileName=attachment_file_path,
    LinkToFile=False,
    DisplayAsIcon=True,  # Display the attachment as an icon
    IconFileName="C:/path/to/icon.ico",  # Optional: specify an icon file path
    IconLabel="Attachment Name"  # Display label for the icon
)

# Save and close the document
doc.SaveAs(r'C:\Users\EDY\Desktop\巡检记录\test\word_test\test.docx')
doc.Close()
word_app.Quit()
