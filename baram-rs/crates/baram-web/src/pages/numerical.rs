use leptos::*;
use crate::components::form_field::{FormField, SelectField};

#[component]
pub fn NumericalPage() -> impl IntoView {
    let (pv_scheme, set_pv_scheme) = create_signal("Simple".to_string());
    let (p_urf, set_p_urf) = create_signal("0.3".to_string());
    let (u_urf, set_u_urf) = create_signal("0.7".to_string());

    view! {
        <div class="page numerical-page">
            <h2>"Numerical Conditions"</h2>

            <section>
                <h3>"Pressure-Velocity Coupling"</h3>
                <SelectField
                    label="Scheme"
                    value=pv_scheme
                    on_change=set_pv_scheme
                    options=vec![("Simple", "SIMPLE"), ("Simplec", "SIMPLEC")]
                />
            </section>

            <section>
                <h3>"Under-Relaxation Factors"</h3>
                <FormField label="Pressure" value=p_urf on_change=set_p_urf input_type="number" />
                <FormField label="Momentum" value=u_urf on_change=set_u_urf input_type="number" />
            </section>

            <div class="page-actions">
                <button class="btn btn-primary">"Apply"</button>
            </div>
        </div>
    }
}
