use leptos::*;
use crate::components::form_field::{FormField, SelectField};

#[component]
pub fn GeneralPage() -> impl IntoView {
    let (flow_type, set_flow_type) = create_signal("Incompressible".to_string());
    let (solver_type, set_solver_type) = create_signal("PressureBased".to_string());
    let (time_mode, set_time_mode) = create_signal("Steady".to_string());
    let (gx, set_gx) = create_signal("0".to_string());
    let (gy, set_gy) = create_signal("-9.81".to_string());
    let (gz, set_gz) = create_signal("0".to_string());
    let (op_pressure, set_op_pressure) = create_signal("101325".to_string());

    view! {
        <div class="page general-page">
            <h2>"General"</h2>

            <section>
                <h3>"Solver Type"</h3>
                <SelectField
                    label="Flow Type"
                    value=flow_type
                    on_change=set_flow_type
                    options=vec![("Incompressible", "Incompressible"), ("Compressible", "Compressible")]
                />
                <SelectField
                    label="Solver"
                    value=solver_type
                    on_change=set_solver_type
                    options=vec![("PressureBased", "Pressure-Based"), ("DensityBased", "Density-Based")]
                />
                <SelectField
                    label="Time"
                    value=time_mode
                    on_change=set_time_mode
                    options=vec![("Steady", "Steady"), ("Transient", "Transient")]
                />
            </section>

            <section>
                <h3>"Gravity"</h3>
                <div class="vector-input">
                    <FormField label="X" value=gx on_change=set_gx input_type="number" />
                    <FormField label="Y" value=gy on_change=set_gy input_type="number" />
                    <FormField label="Z" value=gz on_change=set_gz input_type="number" />
                </div>
            </section>

            <section>
                <h3>"Operating Conditions"</h3>
                <FormField label="Operating Pressure (Pa)" value=op_pressure on_change=set_op_pressure input_type="number" />
            </section>

            <div class="page-actions">
                <button class="btn btn-primary">"Apply"</button>
            </div>
        </div>
    }
}
