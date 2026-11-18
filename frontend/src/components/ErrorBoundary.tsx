/** Global Error Boundary for catching and displaying unhandled React crashes. */

import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('Unhandled React error caught by ErrorBoundary:', error, errorInfo);
  }

  handleReload = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="app-layout">
          <header className="app-header">
            <div className="container">
              <div className="app-header-inner">
                <h1 className="app-title">Isekai: A Life Unwritten</h1>
              </div>
            </div>
          </header>

          <main className="app-main container">
            <section className="app-content">
              <div className="card">
                <div className="card-header">
                  <h2 className="card-title text-crimson">Application Error</h2>
                </div>
                <div className="alert alert-error" role="alert">
                  <p className="alert-title">A fatal error occurred</p>
                  <p className="alert-message">
                    {this.state.error?.message || 'An unexpected rendering error occurred.'}
                  </p>
                </div>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={this.handleReload}
                >
                  Reload Application
                </button>
              </div>
            </section>
          </main>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
