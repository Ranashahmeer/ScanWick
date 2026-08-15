import { useState } from "react"
import { Eye, EyeOff } from "lucide-react"
import {
  Field,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"

const FormField = ({field, fieldState, label, id, type, placeholder}:any) => {
  // Only password fields ever get the show/hide toggle -- every other
  // field type renders exactly as before.
  const [showPassword, setShowPassword] = useState(false)
  const isPassword = type === "password"
  const resolvedType = isPassword && showPassword ? "text" : type

  return (
    <>
        <Field data-invalid={fieldState.invalid}>
            <FieldLabel className="text-gray-500" htmlFor={id}>
                {label}
            </FieldLabel>
            <div className="relative">
                <Input
                    {...field}
                    id={id}
                    aria-invalid={fieldState.invalid}
                    placeholder={placeholder}
                    type={resolvedType}
                    autoComplete="off"
                    className={`bg-slate-50 rounded-[5px] border border-gray-200 ${isPassword ? "pr-8" : ""}`}
                />
                {isPassword && (
                    <button
                        type="button"
                        onClick={() => setShowPassword((current) => !current)}
                        aria-label={showPassword ? "Hide password" : "Show password"}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                        {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                )}
            </div>
        </Field>
    </>
  )
}

export default FormField