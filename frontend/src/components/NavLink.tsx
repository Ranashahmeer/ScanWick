import {Link} from '@tanstack/react-router' 

const NavLink = ({path, name, styleCls}: any) => {
  return (
    <Link to={path} className={styleCls}>{name}</Link>
  )
}

export default NavLink