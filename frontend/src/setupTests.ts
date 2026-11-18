import '@testing-library/jest-dom';

// Flag for React 18 act() environment support in Jest/jsdom
// @ts-expect-error IS_REACT_ACT_ENVIRONMENT is a global flag recognized by React 18
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
