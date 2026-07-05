document.querySelectorAll('.delete-link').forEach(link=>{
  link.addEventListener('click',e=>{if(!confirm('¿Desea desactivar este registro?'))e.preventDefault()})
})
const product=document.getElementById('saleProduct')
if(product) product.addEventListener('change',()=>{
  document.getElementById('salePrice').value=product.selectedOptions[0]?.dataset.price||''
})

