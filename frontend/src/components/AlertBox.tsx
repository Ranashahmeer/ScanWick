import { AlertCircleIcon, CheckCircle2Icon } from "lucide-react"
import {Alert, AlertTitle} from "@/components/ui/alert"

const AlertBox = ({message, messageType} : any) => {
  
  const typeConfig = messageType === "success" ? {
    bgcolor: "bg-green-50", 
    textColor: "text-green-600",
    icon: <CheckCircle2Icon color="#18DC60" />
  } :
  {
    bgcolor: "bg-red-50", 
    textColor: "text-red-600",
    icon: <AlertCircleIcon color="#DC2626" />

  }
 
  return (        
    <Alert className={`${typeConfig.bgcolor} ${typeConfig.textColor}`}>
      {typeConfig.icon}
      <AlertTitle>
        {message}
      </AlertTitle>
    </Alert>
  )
}

export default AlertBox