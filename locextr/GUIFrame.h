///////////////////////////////////////////////////////////////////////////
// C++ code generated with wxFormBuilder (version Apr 16 2008)
// http://www.wxformbuilder.org/
//
// PLEASE DO "NOT" EDIT THIS FILE!
///////////////////////////////////////////////////////////////////////////

#ifndef __GUIFrame__
#define __GUIFrame__

#include <wx/string.h>
#include <wx/bitmap.h>
#include <wx/image.h>
#include <wx/icon.h>
#include <wx/menu.h>
#include <wx/gdicmn.h>
#include <wx/font.h>
#include <wx/colour.h>
#include <wx/settings.h>
#include <wx/statusbr.h>
#include <wx/stattext.h>
#include <wx/textctrl.h>
#include <wx/statline.h>
#include <wx/filepicker.h>
#include <wx/choice.h>
#include <wx/sizer.h>
#include <wx/panel.h>
#include <wx/frame.h>

///////////////////////////////////////////////////////////////////////////

#define idMenuQuit 1000
#define idMenuAbout 1001

///////////////////////////////////////////////////////////////////////////////
/// Class GUIFrame
///////////////////////////////////////////////////////////////////////////////
class GUIFrame : public wxFrame 
{
	private:
	
	protected:
		wxMenuBar* mbar;
		wxMenu* fileMenu;
		wxMenu* helpMenu;
		wxStatusBar* statusBar;
		wxPanel* m_panel2;
		wxStaticText* m_staticText1;
		wxTextCtrl* m_txtResult;
		wxStaticLine* m_staticline1;
		wxStaticText* m_staticText2;
		wxTextCtrl* m_txtSource;
		wxStaticText* m_staticText5;
		wxStaticText* m_staticText51;
		wxStaticText* m_staticText52;
		wxStaticText* m_staticText53;
		wxStaticText* m_staticText3;
		wxStaticText* m_staticText31;
		wxFilePickerCtrl* m_fileOpenFix;
		wxChoice* m_chll1;
		wxTextCtrl* m_txtStart;
		wxFilePickerCtrl* m_fileSave;
		wxStaticText* m_staticText4;
		wxFilePickerCtrl* m_fileOpenAdif;
		wxChoice* m_chll2;
		
		// Virtual event handlers, overide them in your derived class
		virtual void OnClose( wxCloseEvent& event ){ event.Skip(); }
		virtual void OnQuit( wxCommandEvent& event ){ event.Skip(); }
		virtual void OnAbout( wxCommandEvent& event ){ event.Skip(); }
		virtual void OnFileFixedChanged( wxFileDirPickerEvent& event ){ event.Skip(); }
		virtual void OnFileSave( wxFileDirPickerEvent& event ){ event.Skip(); }
		virtual void OnFileAdifChanged( wxFileDirPickerEvent& event ){ event.Skip(); }
		
	
	public:
		GUIFrame( wxWindow* parent, wxWindowID id = wxID_ANY, const wxString& title = wxT("Extract Locator"), const wxPoint& pos = wxDefaultPosition, const wxSize& size = wxSize( 620,466 ), long style = wxDEFAULT_FRAME_STYLE|wxTAB_TRAVERSAL );
		~GUIFrame();
	
};

#endif //__GUIFrame__
