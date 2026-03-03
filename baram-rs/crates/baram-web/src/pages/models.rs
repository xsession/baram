use leptos::*;
use crate::components::form_field::SelectField;

#[component]
pub fn ModelsPage() -> impl IntoView {
    let (turb_model, set_turb_model) = create_signal("KEpsilon".to_string());
    let (multiphase, set_multiphase) = create_signal("Off".to_string());
    let (energy, set_energy) = create_signal("false".to_string());

    view! {
        <div class="page models-page">
            <h2>"Models"</h2>

            <section>
                <h3>"Turbulence"</h3>
                <SelectField
                    label="Model"
                    value=turb_model
                    on_change=set_turb_model
                    options=vec![
                        ("Inviscid", "Inviscid"),
                        ("Laminar", "Laminar"),
                        ("SpalartAllmaras", "Spalart-Allmaras"),
                        ("KEpsilon", "k-ε"),
                        ("KOmega", "k-ω SST"),
                        ("Des", "DES"),
                        ("Les", "LES"),
                    ]
                />
            </section>

            <section>
                <h3>"Multiphase"</h3>
                <SelectField
                    label="Model"
                    value=multiphase
                    on_change=set_multiphase
                    options=vec![("Off", "Off"), ("VolumeOfFluid", "Volume of Fluid")]
                />
            </section>

            <section>
                <h3>"Energy"</h3>
                <SelectField
                    label="Include Energy"
                    value=energy
                    on_change=set_energy
                    options=vec![("false", "Off"), ("true", "On")]
                />
            </section>

            <div class="page-actions">
                <button class="btn btn-primary">"Apply"</button>
            </div>
        </div>
    }
}
