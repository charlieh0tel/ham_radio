// Ambient shims for the UMD globals the pages load from a CDN.
// The pages call the React 18 root API off the global, which the legacy
// @types/react-dom UMD namespace does not declare.
import { Root } from 'react-dom/client';

declare global {
  namespace ReactDOM {
    function createRoot(container: Element | DocumentFragment): Root;
  }
}

// CDN globals used by antenna-matching.html and sherwood.html.  These are
// deliberately loose: they exist so the pages can be checked at all, not to
// model the libraries.  Tighten a member when a bug would be caught by it.
declare const math: any;
declare const fmin: any;
declare const Chart: any;
