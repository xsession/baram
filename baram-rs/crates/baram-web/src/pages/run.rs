use leptos::*;
use crate::components::form_field::FormField;
use crate::components::residual_chart::ResidualChart;

#[component]
pub fn RunPage() -> impl IntoView {
    let (iterations, set_iterations) = create_signal("1000".to_string());
    let (save_interval, set_save_interval) = create_signal("100".to_string());

    view! {
        <div class="page run-page">
            <h2>"Run Conditions"</h2>

            <section>
                <h3>"Iteration / Time"</h3>
                <FormField label="Number of Iterations" value=iterations on_change=set_iterations input_type="number" />
                <FormField label="Save Interval"        value=save_interval on_change=set_save_interval input_type="number" />
            </section>

            <section>
                <h3>"Convergence"</h3>
                <ResidualChart field="p".to_string() />
            </section>

            <div class="page-actions">
                <button class="btn btn-success">"▶ Start Calculation"</button>
                <button class="btn btn-danger">"■ Stop"</button>
            </div>
        </div>
    }
}
