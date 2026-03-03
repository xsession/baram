use leptos::*;
use crate::components::form_field::{FormField, SelectField};
use crate::components::residual_chart::ResidualChart;

#[component]
pub fn RunPage() -> impl IntoView {
    let (iterations, set_iterations) = create_signal("1000".to_string());
    let (save_interval, set_save_interval) = create_signal("100".to_string());
    let (active_backend, set_active_backend) = create_signal("open_foam".to_string());
    let (solver_status, _set_solver_status) = create_signal("Idle".to_string());

    view! {
        <div class="page run-page">
            <h2>"Run Conditions"</h2>

            <section class="card">
                <div class="card-header">"Solver Backend"</div>
                <SelectField
                    label="Active Solver"
                    value=active_backend
                    on_change=set_active_backend
                    options=vec![
                        ("open_foam", "OpenFOAM (FVM)"),
                        ("elmer",     "Elmer FEM"),
                        ("fluid_x3d", "FluidX3D (LBM/GPU)"),
                    ]
                />
                <div class="flex items-center gap-2" style="margin-top:8px">
                    <span class="text-sm text-muted">"Status: "</span>
                    <span class="badge badge-accent">{solver_status}</span>
                </div>
            </section>

            <section class="card">
                <div class="card-header">"Iteration / Time"</div>
                <FormField label="Number of Iterations" value=iterations on_change=set_iterations input_type="number" />
                <FormField label="Save Interval"        value=save_interval on_change=set_save_interval input_type="number" />
            </section>

            <section class="card">
                <div class="card-header">"Convergence"</div>
                <ResidualChart field="p".to_string() />
            </section>

            <div class="page-actions">
                <button class="btn btn-success">"▶ Start Calculation"</button>
                <button class="btn btn-danger">"■ Stop"</button>
            </div>
        </div>
    }
}
