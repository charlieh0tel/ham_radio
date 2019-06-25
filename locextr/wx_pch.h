/***************************************************************
 * Name:      wx_pch.h
 * Purpose:   Header to create Pre-Compiled Header (PCH)
 * Author:    Roger Hedin (sm3gsj<a>qsl.net)
 * Created:   2010-05-09
 * Copyright: Roger Hedin (http://www.qsl.net/sm3gsj)
 * License:   Free for personal use.If you modify it and make it
              better - please email me a copy!
 **************************************************************/

#ifndef WX_PCH_H_INCLUDED
#define WX_PCH_H_INCLUDED

// basic wxWidgets headers

//#include <wx/wxprec.h>

#ifdef __BORLANDC__
    #pragma hdrstop
#endif

#ifndef WX_PRECOMP
    #include <wx/wx.h>
#endif

#ifdef WX_PRECOMP
    // put here all your rarely-changing header files
#include <wx/msgdlg.h>
#include <wx/file.h>
#include <wx/ffile.h>
#include <wx/textfile.h>

#endif // WX_PRECOMP

#endif // WX_PCH_H_INCLUDED
