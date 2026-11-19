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

      const isId = typeof window !== 'undefined' && localStorage.getItem('isekai_language') === 'id';

      return (
        <div className="app-layout">
          <header className="app-header">
            <div className="container">
              <div className="app-header-inner">
                <h1 className="app-title">{isId ? 'Isekai: Takdir Tak Tertulis' : 'Isekai: A Life Unwritten'}</h1>
              </div>
            </div>
          </header>

          <main className="app-main container">
            <section className="app-content">
              <div className="card">
                <div className="card-header">
                  <h2 className="card-title text-crimson">{isId ? 'Kesalahan Aplikasi' : 'Application Error'}</h2>
                </div>
                <div className="alert alert-error" role="alert">
                  <p className="alert-title">{isId ? 'Terjadi kesalahan sistem yang tidak terduga' : 'A fatal error occurred'}</p>
                  <p className="alert-message">
                    {this.state.error?.message || (isId ? 'Terjadi kesalahan render yang tidak terduga.' : 'An unexpected rendering error occurred.')}
                  </p>
                </div>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={this.handleReload}
                >
                  {isId ? 'Muat Ulang Aplikasi' : 'Reload Application'}
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
