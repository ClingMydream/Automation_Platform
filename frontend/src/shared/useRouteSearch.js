import React,{useEffect,useState}from'react';

// pushState does not emit popstate; the platform emits its own location event.
export function useRouteSearch(){
 const [search,setSearch]=useState(()=>location.search);
 useEffect(()=>{const sync=()=>setSearch(location.search);window.addEventListener('popstate',sync);window.addEventListener('cling:location',sync);return()=>{window.removeEventListener('popstate',sync);window.removeEventListener('cling:location',sync);};},[]);
 return new URLSearchParams(search);
}
