import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

const FormField = ({
  field,
  fieldState,
  label,
  id,
  type,
  placeholder,
}: {
  field: any;
  fieldState: any;
  label?: string;
  id: string;
  type?: string;
  placeholder?: string;
}) => {
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === "password";
  const resolvedType = isPassword && showPassword ? "text" : type;

  return (
    <Field data-invalid={fieldState.invalid} className="w-full">
      {label ? (
        <FieldLabel
          className="text-xs font-semibold text-[#3E4A44] mb-1.5 block tracking-tight"
          htmlFor={id}
        >
          {label}
        </FieldLabel>
      ) : null}
      <div className="relative w-full">
        <Input
          {...field}
          id={id}
          aria-invalid={fieldState.invalid}
          placeholder={placeholder}
          type={resolvedType}
          autoComplete="off"
          className={`h-11 w-full bg-white rounded-lg border text-sm text-[#0E1512] placeholder:text-[#6B7A72]/60 transition-all duration-150 ${
            fieldState.invalid
              ? "border-[#9B2C2C] focus:border-[#9B2C2C] focus:ring-2 focus:ring-[#9B2C2C]/20"
              : "border-[#DCE3DF] hover:border-[#7FC7A3] focus:border-[#1B7A4B] focus:ring-2 focus:ring-[#1B7A4B]/20"
          } ${isPassword ? "pr-10" : ""}`}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword((current) => !current)}
            aria-label={showPassword ? "Hide password" : "Show password"}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-[#6B7A72] hover:text-[#0E1512] transition-colors"
          >
            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        )}
      </div>
    </Field>
  );
};

export default FormField;