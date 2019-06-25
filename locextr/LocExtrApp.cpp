/***************************************************************
 * Name:      LocExtrApp.cpp
 * Purpose:   Code for Application Class
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

#include "LocExtrApp.h"
#include "LocExtrMain.h"

IMPLEMENT_APP(LocExtrApp);

bool LocExtrApp::OnInit()
{
    LocExtrFrame* frame = new LocExtrFrame(0L);
    frame->Show();

    return true;
}
