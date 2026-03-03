use leptos::*;

/// A labeled form field with an input element.
#[component]
pub fn FormField(
    label: &'static str,
    value: ReadSignal<String>,
    on_change: WriteSignal<String>,
    #[prop(default = "text")] input_type: &'static str,
) -> impl IntoView {
    view! {
        <div class="form-field">
            <label>{label}</label>
            <input
                type=input_type
                prop:value=value
                on:input=move |ev| {
                    let v = event_target_value(&ev);
                    on_change.set(v);
                }
            />
        </div>
    }
}

/// A labeled select dropdown.
#[component]
pub fn SelectField(
    label: &'static str,
    value: ReadSignal<String>,
    on_change: WriteSignal<String>,
    options: Vec<(&'static str, &'static str)>, // (value, display)
) -> impl IntoView {
    view! {
        <div class="form-field">
            <label>{label}</label>
            <select
                prop:value=value
                on:change=move |ev| {
                    let v = event_target_value(&ev);
                    on_change.set(v);
                }
            >
                {options.into_iter().map(|(val, display)| {
                    view! { <option value=val>{display}</option> }
                }).collect_view()}
            </select>
        </div>
    }
}
