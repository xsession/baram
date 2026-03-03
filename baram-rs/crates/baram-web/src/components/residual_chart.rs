use leptos::*;

/// Simple residual chart placeholder.
/// A real implementation would use an HTML canvas or SVG to draw the
/// convergence history. This is a scaffold for the chart component.
#[component]
pub fn ResidualChart(
    #[prop(default = "p".to_string())] field: String,
) -> impl IntoView {
    view! {
        <div class="residual-chart">
            <h4>"Residuals — " {field.clone()}</h4>
            <div class="chart-placeholder">
                <svg viewBox="0 0 400 200" width="100%" height="200">
                    <rect x="0" y="0" width="400" height="200" fill="#1e1e2e" rx="4"/>
                    <text x="200" y="100" text-anchor="middle" fill="#888" font-size="14">
                        "No data yet — run solver to see residuals"
                    </text>
                </svg>
            </div>
        </div>
    }
}
