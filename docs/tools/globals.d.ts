// Ambient shims for the UMD globals the pages load from a CDN.
// The pages call the React 18 root API off the global, which the legacy
// @types/react-dom UMD namespace does not declare.
import { Root } from 'react-dom/client';

declare global {
  namespace ReactDOM {
    function createRoot(container: Element | DocumentFragment): Root;
  }
}

// mathjs, as antenna-matching.html uses it: complex arithmetic and nothing
// else.  Only the members the page calls are declared, and only over the
// argument types it passes.  The point is to catch a real/imaginary mixup or
// a Complex used where a number belongs, not to model mathjs.
declare global {
  interface Complex {
    re: number;
    im: number;
  }

  /** Either operand of the complex helpers may be a bare real. */
  type Numeric = Complex | number;

  const math: {
    complex(re: number, im: number): Complex;
    add(a: Numeric, b: Numeric): Complex;
    subtract(a: Numeric, b: Numeric): Complex;
    multiply(a: Numeric, b: Numeric): Complex;
    divide(a: Numeric, b: Numeric): Complex;
    sqrt(a: Numeric): Complex;
  };

  // fmin's Nelder-Mead simplex minimizer.  `x` is the solution vector, in the
  // same order as the initial guess; `fx` is the objective there.
  const fmin: {
    nelderMead(
      objective: (x: number[]) => number,
      initial: number[],
    ): { x: number[]; fx: number };
  };

  // Chart.js is used by sherwood.html only, through its constructor and the
  // instance's update/destroy.  Left loose: nothing here would catch a bug.
  const Chart: any;
}
