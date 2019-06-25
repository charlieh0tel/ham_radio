/***************************************************************
 * Name:      LocExtrMain.h
 * Purpose:   Defines Application Frame
 * Author:    Roger Hedin (sm3gsj@qsl.net)
 * Created:   2010-05-09
 * Copyright: Roger Hedin (http://www.qsl.net/sm3gsj)
 * License:   Free for personal use.If you modify it and make it
              better - please email me a copy!
 **************************************************************/

#ifndef LocExtrMAIN_H
#define LocExtrMAIN_H



#include "LocExtrApp.h"


#include "GUIFrame.h"

class LocExtrFrame: public GUIFrame
{
    public:
        LocExtrFrame(wxFrame *frame);
        ~LocExtrFrame();
    private:

        bool Loc2Deg(double *lat, double *lon, wxString loc);
        virtual void OnClose(wxCloseEvent& event);
        virtual void OnQuit(wxCommandEvent& event);
        virtual void OnAbout(wxCommandEvent& event);
        void OnFileFixedChanged( wxFileDirPickerEvent& event );
		void OnFileSave( wxFileDirPickerEvent& event );
		void OnFileAdifChanged( wxFileDirPickerEvent& event );

};

#endif // LocExtrMAIN_H
