/***************************************************************
 * Name:      LocExtrMain.cpp
 * Purpose:   Code for Application Frame
 * Author:    Roger Hedin (sm3gsj@qsl.net)
 * Created:   2010-05-09
 * Copyright: Roger Hedin (http://www.qsl.net/sm3gsj)
 * License:   Free for personal use.If you modify it and make it
              better - please email me a copy!
 **************************************************************/

#ifdef WX_PRECOMP
#include "wx_pch.h"
#endif

#ifdef __BORLANDC__
#pragma hdrstop
#endif //__BORLANDC__

#include "LocExtrMain.h"

//helper functions
enum wxbuildinfoformat
{
    short_f, long_f
};

wxString wxbuildinfo(wxbuildinfoformat format)
{
    wxString wxbuild(wxVERSION_STRING);

    if (format == long_f )
    {
#if defined(__WXMSW__)
        wxbuild << _T("-Windows");
#elif defined(__WXMAC__)
        wxbuild << _T("-Mac");
#elif defined(__UNIX__)
        wxbuild << _T("-Linux");
#endif

#if wxUSE_UNICODE
        wxbuild << _T("-Unicode build");
#else
        wxbuild << _T("-ANSI build");
#endif // wxUSE_UNICODE
    }

    return wxbuild;
}


LocExtrFrame::LocExtrFrame(wxFrame *frame)
        : GUIFrame(frame)
{
#if wxUSE_STATUSBAR
    statusBar->SetStatusText(_("Extract Locators from text files"), 0);
    statusBar->SetStatusText(wxbuildinfo(short_f), 1);
#endif


}

//***************************************************************
// Name:      OnFileFixedChanged( wxFileDirPickerEvent& event )
// Arguments: event = unused
// Purpose:   Called when the fixed (ie get 4 letters from position
//            xx in line) filepicker is called.
//**************************************************************/
void LocExtrFrame::OnFileFixedChanged( wxFileDirPickerEvent& WXUNUSED(event) )
{
    //Clear the source and result textboxes
    m_txtSource->Clear();
    m_txtResult->Clear();

    wxTextFile doc;

    // try to open the the file
    if (!doc.Open(m_fileOpenFix->GetPath()))
        return;

    wxString str;
    double la,lo;
    long loccnt, loclen;
    unsigned int cnt;


    // iterate through the text file
    for (cnt = 0; cnt < doc.GetLineCount(); cnt++)
    {
        str = doc.GetLine(cnt).MakeUpper(); //Make the line upper case
        m_txtSource->AppendText(str + wxT('\n')); // Fill the source textbox with the read line

        // Every 10:th row - insert number lines
        if (!(cnt % 10))
        {
            m_txtSource->AppendText(wxT("01234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890\n"));
            m_txtSource->AppendText(wxT("          1         2         3         4         5         6         7         8         9         0\n"));
        }

        //Get the start position for the locator in the line
        m_txtStart->GetValue().ToLong(&loccnt);

        //Get the number of letters to extract (4 or 6) Doesn't really matter - only 4 is used anyway
        m_chll1->GetString(m_chll1->GetSelection()).ToLong(&loclen);

        //Chect if we read past end of line
        if ((unsigned long)(loccnt+loclen) <= str.Len())
        {
            //Check if it is a valid locator
            if (Loc2Deg(&la,&lo,str.Mid(loccnt,loclen)))
            {
                //Fill the result textbox
                m_txtResult->AppendText(str.Mid(loccnt,loclen) + wxT('\n'));
            }
        }

    }

}

//***************************************************************
// Name:      OnFileSave( wxFileDirPickerEvent& event )
// Arguments: event = unused
// Purpose:   Called when the Save file picker is chosen
//**************************************************************/
void LocExtrFrame::OnFileSave( wxFileDirPickerEvent& WXUNUSED(event) )
{
    wxFile file;
    wxString str;

    // Check if we could open the file for writing
    if (!file.Open(m_fileSave->GetPath(), wxFile::write))
        return;

    //Get the number of lines in the text control
    int nLines = m_txtResult->GetNumberOfLines();

    for ( int nLine = 0; nLine < nLines; nLine++ )
    {
        file.Write(m_txtResult->GetLineText(nLine) + wxTextFile::GetEOL());
    }
    file.Close();
}


//***************************************************************
// Name:      OnFileAdifChanged( wxFileDirPickerEvent& event )
// Arguments: event = unused
// Purpose:   Called when the file picker for Adif files is chosen
//**************************************************************/
void LocExtrFrame::OnFileAdifChanged( wxFileDirPickerEvent& WXUNUSED(event) )
{
    //Clear the source and result textboxes
    m_txtSource->Clear();
    m_txtResult->Clear();

    wxTextFile doc;

    // try to open the the file
    if (!doc.Open(m_fileOpenAdif->GetPath()))
        return;

    wxString str;
    double la,lo;
    long loclen=0;

    //How many letters to check in the line (4 or 6)
    m_chll2->GetString(m_chll2->GetSelection()).ToLong(&loclen);

    for (unsigned int cnt = 0; cnt < doc.GetLineCount(); cnt++)
    {
        //Make the line upper case
        str = doc.GetLine(cnt).MakeUpper();

        //Fill the source textbox
        m_txtSource->AppendText(str + wxT('\n'));

        //Start at the beginning of the line - extract 4 or 6 letters
        //Check if it is a valid locator (Loc2Deg returns true)
        for (unsigned int cnt1=0; cnt1 < str.Len(); cnt1++)
        {
            if (Loc2Deg(&la,&lo,str.Mid(cnt1,loclen)))
            {
                //Result was a locator - Fill result textbox with the locator
                m_txtResult->AppendText(str.Mid(cnt1,loclen) + wxT('\n'));
            }
        }

    }


}

//***************************************************************
// Name:      Loc2Deg(double *lat, double *lon, wxString loc)
// Arguments: lat = returns the latitude as a double (degrees North positive)
//            lon = returns the longitude as a double (degrees East positive)
//            loc = wxString 4 or 6 letter locator
// returns:   bool true if the locator is valid - false otherwise
// Purpose:   Translate locator to lat/lon
//**************************************************************/
bool LocExtrFrame::Loc2Deg(double *lat, double *lon, wxString loc)
{

    //Add "LL" if only 4 letters in locator
    if (loc.Len() == 4)
    {
        loc.Append('L',2);
    }

    if (loc.Len() == 6)
    {
        //Check if in valid range AA00AA to RR99XX
        if ((loc.GetChar(0) > 'R') || (loc.GetChar(0) < 'A')) return(false);
        if ((loc.GetChar(1) > 'R') || (loc.GetChar(1) < 'A')) return(false);
        if ((loc.GetChar(2) > '9') || (loc.GetChar(2) < '0')) return(false);
        if ((loc.GetChar(3) > '9') || (loc.GetChar(3) < '0')) return(false);
        if ((loc.GetChar(4) > 'X') || (loc.GetChar(4) < 'A')) return(false);
        if ((loc.GetChar(5) > 'X') || (loc.GetChar(5) < 'A')) return(false);

        //Calculate lat and lon

        *lon = (loc.GetChar(0) - 65) * 20.0 - 180.0 + (loc.GetChar(2) - 48) * 2.0 + (loc.GetChar(4) - 65) / 12.0 + 1.0 / 24.0;
        *lat = (loc.GetChar(1) - 65) * 10.0 - 90.0 + (loc.GetChar(3) - 48) + (loc.GetChar(5) - 65) / 24.0 + 1.0 / 48.0;
        return true;
    }
    return(false);
}

LocExtrFrame::~LocExtrFrame()
{
}

void LocExtrFrame::OnClose(wxCloseEvent& WXUNUSED(event))
{
    Destroy();
}

void LocExtrFrame::OnQuit(wxCommandEvent& WXUNUSED(event))
{
    Destroy();
}

void LocExtrFrame::OnAbout(wxCommandEvent& WXUNUSED(event))
{
    wxString msg = wxbuildinfo(long_f);
    wxMessageBox(msg, _("Welcome to..."));
}
