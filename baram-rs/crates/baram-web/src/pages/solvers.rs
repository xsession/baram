use leptos::*;
use crate::components::form_field::SelectField;

// ════════════════════════════════════════════════════════════════
//  Solvers Page — configure solver backends (OpenFOAM/Elmer/FluidX3D)
// ════════════════════════════════════════════════════════════════

#[component]
pub fn SolversPage() -> impl IntoView {
    let (active_backend, set_active_backend) = create_signal("open_foam".to_string());
    let (openfoam_enabled, set_openfoam_enabled) = create_signal(true);
    let (elmer_enabled, set_elmer_enabled) = create_signal(false);
    let (fluidx3d_enabled, set_fluidx3d_enabled) = create_signal(false);

    // OpenFOAM settings
    let (of_mpi, set_of_mpi) = create_signal("mpirun".to_string());
    let (of_cores, set_of_cores) = create_signal("4".to_string());

    // Elmer settings
    let (elmer_partitions, set_elmer_partitions) = create_signal("1".to_string());

    // FluidX3D settings
    let (fx3d_gpu, set_fx3d_gpu) = create_signal("auto".to_string());
    let (fx3d_resolution, set_fx3d_resolution) = create_signal("0".to_string());

    view! {
        <div class="page solvers-page">
            <h2>"Solver Backends"</h2>

            // ─── Active backend selector ──────────────────
            <section class="card">
                <div class="card-header">"Active Solver"</div>
                <SelectField
                    label="Primary Solver Backend"
                    value=active_backend
                    on_change=set_active_backend
                    options=vec![
                        ("open_foam", "OpenFOAM (FVM)"),
                        ("elmer",     "Elmer FEM"),
                        ("fluid_x3d", "FluidX3D (LBM/GPU)"),
                    ]
                />
                <p class="text-sm text-muted" style="margin-top:8px">
                    "Select which solver engine to use when running the simulation."
                </p>
            </section>

            // ─── Enabled backends (checkboxes) ────────────
            <section class="card">
                <div class="card-header">"Enabled Backends"</div>
                <p class="text-sm text-muted" style="margin-bottom:12px">
                    "Enable the solver backends you have installed. You can switch between them at any time."
                </p>
                <div class="backend-toggles">
                    <label class="backend-toggle">
                        <input
                            type="checkbox"
                            prop:checked=openfoam_enabled
                            on:change=move |_| set_openfoam_enabled.update(|v| *v = !*v)
                        />
                        <div class="backend-info">
                            <strong>"OpenFOAM"</strong>
                            <span class="text-sm text-muted">" — Finite Volume Method, industry standard for CFD"</span>
                        </div>
                    </label>
                    <label class="backend-toggle">
                        <input
                            type="checkbox"
                            prop:checked=elmer_enabled
                            on:change=move |_| set_elmer_enabled.update(|v| *v = !*v)
                        />
                        <div class="backend-info">
                            <strong>"Elmer FEM"</strong>
                            <span class="text-sm text-muted">" — Finite Element Method, multi-physics (CSC Finland)"</span>
                        </div>
                    </label>
                    <label class="backend-toggle">
                        <input
                            type="checkbox"
                            prop:checked=fluidx3d_enabled
                            on:change=move |_| set_fluidx3d_enabled.update(|v| *v = !*v)
                        />
                        <div class="backend-info">
                            <strong>"FluidX3D"</strong>
                            <span class="text-sm text-muted">" — Lattice-Boltzmann GPU solver, massively parallel"</span>
                        </div>
                    </label>
                </div>
            </section>

            // ─── OpenFOAM settings ────────────────────────
            <Show when=move || openfoam_enabled.get() fallback=|| ()>
                <section class="card">
                    <div class="card-header">"OpenFOAM Settings"</div>
                    <div class="form-group">
                        <label>"Install Directory"</label>
                        <input type="text" placeholder="Auto-detect from PATH" />
                    </div>
                    <FormFieldInline label="MPI Command" value=of_mpi on_change=set_of_mpi />
                    <FormFieldInline label="CPU Cores" value=of_cores on_change=set_of_cores />
                </section>
            </Show>

            // ─── Elmer settings ───────────────────────────
            <Show when=move || elmer_enabled.get() fallback=|| ()>
                <section class="card">
                    <div class="card-header">"Elmer FEM Settings"</div>
                    <div class="form-group">
                        <label>"Install Directory"</label>
                        <input type="text" placeholder="Auto-detect from PATH" />
                    </div>
                    <FormFieldInline label="Mesh Partitions" value=elmer_partitions on_change=set_elmer_partitions />
                </section>
            </Show>

            // ─── FluidX3D settings ────────────────────────
            <Show when=move || fluidx3d_enabled.get() fallback=|| ()>
                <section class="card">
                    <div class="card-header">"FluidX3D Settings"</div>
                    <div class="form-group">
                        <label>"Install Directory"</label>
                        <input type="text" placeholder="Auto-detect from PATH" />
                    </div>
                    <SelectField
                        label="GPU Device"
                        value=fx3d_gpu
                        on_change=set_fx3d_gpu
                        options=vec![
                            ("auto", "Auto (fastest available)"),
                            ("0",    "GPU 0"),
                            ("1",    "GPU 1"),
                            ("2",    "GPU 2"),
                        ]
                    />
                    <FormFieldInline label="Lattice Resolution (0 = auto)" value=fx3d_resolution on_change=set_fx3d_resolution />
                </section>
            </Show>

            <div class="page-actions">
                <button class="btn btn-primary">"Apply"</button>
            </div>
        </div>
    }
}

/// Compact inline form field for settings panels.
#[component]
fn FormFieldInline(
    label: &'static str,
    value: ReadSignal<String>,
    on_change: WriteSignal<String>,
) -> impl IntoView {
    view! {
        <div class="form-group">
            <label>{label}</label>
            <input
                type="text"
                prop:value=value
                on:input=move |ev| {
                    let v = event_target_value(&ev);
                    on_change.set(v);
                }
            />
        </div>
    }
}
